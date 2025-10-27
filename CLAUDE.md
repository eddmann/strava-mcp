# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Model Context Protocol (MCP) server that enables LLMs to interact with the Strava API. Built with Python 3.11+ using FastMCP framework. Provides 11 tools organized into 5 categories (Activities, Athlete, Segments, Routes, Analysis), plus 1 MCP resource and 6 MCP prompts.

**Dual-Mode Support**: The server supports both stdio (Claude Desktop) and HTTP (ChatGPT, Lambda) transports with unified client implementation.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
uv sync

# Stdio mode: Run authentication setup (interactive OAuth flow)
uv run strava-mcp-auth

# Run the MCP server in stdio mode (default, for Claude Desktop)
uv run strava-mcp

# Run the MCP server in HTTP mode (for ChatGPT, Lambda)
uv run strava-mcp --transport http
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_activity_tools.py

# Run tests with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_query_activities"
```

### Linting and Type Checking
```bash
# Format code with ruff
uv run ruff format .

# Run linter
uv run ruff check .

# Run type checker
uv run pyright
```

## Code Architecture

### Core Components

**server.py** - MCP server entry point
- `create_server(transport_mode)` function creates and configures FastMCP instance for stdio or HTTP mode
- Conditionally imports and configures mode-specific middleware and auth providers
- Registers all tools, resources, and prompts (transport-agnostic)
- Tools are registered by importing functions from `tools/` modules and wrapping them with `@mcp.tool()` decorator
- MCP resources defined with `@mcp.resource()` decorator (provides ongoing context without explicit tool calls)
- MCP prompts defined with `@mcp.prompt()` decorator (templates for common queries)
  - Includes `race_performance_analysis` prompt for analyzing race performance by distance
- `main()` function parses CLI arguments and runs server with selected transport

**client.py** - Strava API client (transport-agnostic)
- Defines `StravaAuthContext` protocol that both stdio and HTTP authentication contexts implement
- Async HTTP client using `httpx`
- Accepts `StravaAuthContext` protocol - works with both stdio and HTTP modes
- Automatic OAuth token refresh on 401 (mode-specific: `.env` for stdio, session store for HTTP)
- Comprehensive error handling with custom `StravaAPIError` exception
- Methods organized by API category: activities, athlete, segments, routes
- All API responses validated using Pydantic models
- **Unified `get_activities()` method** replaces three separate methods with comprehensive client-side filtering:
  - Supports filtering by: `activity_type`, `distance_min`, `distance_max`, `title_contains`, `is_race`
  - Returns tuple `(activities, is_exhausted)` to indicate if more data is available from Strava
  - Implements safety limits: 5 API calls with filters, 10 without (prevents excessive requests during pagination)

**stdio_middleware.py** - Stdio mode request middleware
- **StdioClientMiddleware**: Loads config from `.env`, creates and injects `StravaClient` per request
- Injects client via `ctx.get_state("client")` for tools to access

**http_middleware.py** - HTTP mode request middleware
- **HttpClientMiddleware**: Resolves OAuth session, creates `HttpStravaAuthContext`, proactively refreshes tokens, injects `StravaClient`
- Extracts OAuth token from MCP request and resolves user session
- Injects client via `ctx.get_state("client")` for tools to access

**stdio_auth.py** - Stdio mode authentication
- `StdioStravaAuthContext` implements `StravaAuthContext` protocol for stdio mode
- Loads tokens from `.env` file via Pydantic settings
- Token refresh persists back to `.env` file
- Interactive setup script in `scripts/setup_auth.py` for initial OAuth flow (supports both stdio and HTTP mode)

**http_auth.py** - HTTP mode OAuth provider
- `StravaOAuthProvider` implements FastMCP OAuth provider interface
- Handles MCP OAuth authorization/token endpoints
- Bridges ChatGPT OAuth flow with Strava OAuth flow
- Manages authorization codes, access tokens, refresh tokens via `SessionStore`

**http_session.py** - HTTP mode authentication and session management
- `HttpStravaAuthContext` implements `StravaAuthContext` protocol for HTTP mode
- `StravaOAuthService` handles two-hop OAuth flow (MCP → Strava)
- `SessionStore` manages per-user sessions (in-memory or DynamoDB)
- Tokens stored in session store, refreshed on demand

**filters.py** - Client-side activity filtering utilities
- **Distance parsing** with flexible formats:
  - Race distance names with ±10% tolerance: `"5k"`, `"10k"`, `"half-marathon"`, `"marathon"`, `"ultra"`
  - Numeric values with units and ±10% buffer: `"10km"`, `"5mi"`, `"10000"` (defaults to meters)
  - Exact ranges: `"5km:10km"`, `"3mi:6mi"`, `":10km"` (open-ended min), `"5mi:"` (open-ended max)
  - Supports units: km, mi, m (case-insensitive)
- **Title filtering**: Case-insensitive substring search in activity names
- **Race detection**: Identifies races by workout_type (Run races=1, Ride races=11)
- **Unified filtering**: `apply_filters()` applies all filters with AND logic

**models.py** - Pydantic models
- Complete type definitions for all Strava API responses
- Uses forward references for circular dependencies (e.g., `DetailedActivity` → `Lap` → `MetaActivity`)
- Type aliases for enums (ActivityType, MeasurementPreference, Sex, etc.)

**response_builder.py** - Structured JSON output
- All tools return consistent JSON structure: `{"data": {...}, "pagination": {...}, "analysis": {...}, "metadata": {...}}`
- Formatting utilities that provide both raw and human-readable values (e.g., distance in meters + formatted string)
- Error responses follow standard format: `{"error": {"message": "...", "type": "...", "suggestions": [...]}}`

**pagination.py** - Pagination utilities
- Cursor-based pagination support for all list-returning tools
- `encode_cursor()` / `decode_cursor()` for opaque cursor strings
- `build_pagination_info()` generates standardized pagination metadata
- Cursors encode page number and query filters for continuity

**formatters.py** - Unit conversion and formatting
- Functions for formatting distance, duration, pace, speed, elevation
- Supports both metric (meters) and imperial (feet) preferences
- Used by `response_builder.py` to generate human-readable output

**time_utils.py** - Time range parsing
- Parses time range strings like "7d", "30d", "ytd", "YYYY-MM-DD:YYYY-MM-DD"
- Used by tools that filter activities by date range

**lambda_handler.py** - AWS Lambda deployment
- Wraps FastMCP ASGI app with Mangum for Lambda compatibility
- Creates server in HTTP mode with streamable-http transport
- Entry point: `handler(event, context)` function

### Tool Organization

Tools are organized into 5 modules under `src/strava_mcp/tools/`:

1. **activities.py** - Query activities with optional enrichment (streams, laps, zones), get social data
   - **New filtering parameters**: `distance`, `title_contains`, `is_race`
   - Distance filter supports race names (`"marathon"`), units (`"10km"`), and ranges (`"5km:10km"`)
   - Cursor validation prevents filter changes mid-pagination
   - Deep pagination protection (max 10 pages with filters to prevent excessive API usage)
2. **athlete.py** - Get athlete profile with optional stats and training zones
3. **segments.py** - Query segments (by ID, starred, or explore), star/unstar, get leaderboard
4. **routes.py** - List routes, get route details, export to GPX/TCX
5. **analysis.py** - Training analysis, activity comparison, similarity search
   - **New filtering parameters**: `distance`, `title_contains`, `is_race` added to `analyze_training` and `find_similar_activities`
   - Enables focused analysis (e.g., analyze only marathon races, or only tempo runs)

All tools follow a consistent pattern:
- Accept parameters with `Annotated[type, "description"]` for MCP schema generation
- Accept `ctx: Context` parameter to access injected `StravaClient` via `ctx.get_state("client")`
- Client is injected by middleware (stdio or HTTP mode) before tool execution
- Return JSON string via `ResponseBuilder.build_response()` or `ResponseBuilder.build_error_response()`
- Handle `StravaAPIError` exceptions with appropriate error messages
- List-returning tools support cursor-based pagination with `cursor` and `limit` parameters

### Testing Strategy

**Test fixtures** (`tests/fixtures/`) - Reusable test data for activities, athletes, routes, segments
**Test stubs** (`tests/stubs/`) - Mock Strava API responses using `respx` library
**Test organization** - One test file per tool module (e.g., `test_activity_tools.py`, `test_filters.py`)
**Async testing** - Uses `pytest-asyncio` with `asyncio_mode = "auto"` (configured in pyproject.toml)

When adding tests:
- Use fixtures from `tests/fixtures/` to create realistic test data
- Mock HTTP responses with `respx` in `tests/stubs/strava_api_stub.py`
- Follow naming convention: `test_<function_name>_<scenario>`
- `test_filters.py` provides comprehensive test coverage for all filtering utilities

### OAuth Flow (Stdio Mode)

1. User runs `uv run strava-mcp-auth`
2. Interactive wizard prompts for transport mode (stdio or http)
3. For stdio mode: Script opens browser to Strava authorization URL
4. User authorizes app, redirected to localhost callback
5. Script exchanges authorization code for tokens
6. Tokens saved to `.env` file (STRAVA_ACCESS_TOKEN, STRAVA_REFRESH_TOKEN)
7. Server loads tokens on startup via `StdioStravaAuthContext()`
8. Client automatically refreshes tokens when expired (401 response)
9. Refreshed tokens persisted back to `.env` file automatically

### OAuth Flow (HTTP Mode)

1. User connects to MCP server from ChatGPT or other MCP client
2. MCP client initiates OAuth flow via `StravaOAuthProvider`
3. User is redirected to Strava authorization URL
4. After authorization, tokens are stored in `SessionStore` (in-memory or DynamoDB)
5. Each subsequent request includes MCP OAuth token
6. `HttpClientMiddleware` resolves session and creates `HttpStravaAuthContext`
7. Client automatically refreshes Strava tokens when expired
8. Refreshed tokens saved back to session store

### Key Design Patterns

**Protocol-based auth context** - `StravaAuthContext` protocol enables unified `StravaClient` implementation for both stdio and HTTP modes

**Middleware injection** - Mode-specific middlewares inject `StravaClient` into context state before tool execution

**Unified query tools** - Single tool handles multiple query patterns (e.g., `query_activities` can get single activity by ID or list activities with filters)

**Structured JSON output** - All tools return consistent JSON structure with raw + formatted values (e.g., distance in meters + "10.5 km")

**Cursor-based pagination** - List tools use opaque cursors for reliable multi-page queries with reduced default limits (10-50 items)

**Error handling hierarchy** - `StravaAPIError` → `ResponseBuilder.build_error_response()` → JSON with error type and suggestions

**Automatic token refresh** - Client handles token refresh transparently without exposing OAuth details to tools

**Type safety** - Comprehensive Pydantic models for all API responses ensure type safety throughout the codebase

**Client-side filtering** - Unified filtering layer (`filters.py`) enables rich query capabilities not supported by Strava API:
- Distance filtering with race names, units, and ranges
- Title substring search
- Race detection based on workout_type
- All filters applied with AND logic for precise queries

## Activity Filtering

The server provides comprehensive client-side filtering capabilities for activities through the `filters.py` module. These filters extend beyond what the Strava API natively supports.

### Supported Filters

#### Distance Filtering

Distance filtering supports three input formats:

1. **Race distance names** (with ±10% tolerance):
   - `"5k"` → 4,500-5,500m
   - `"10k"` → 9,000-11,000m
   - `"15k"` → 13,500-16,500m
   - `"half-marathon"`, `"half marathon"`, `"half"` → 20,000-22,000m
   - `"marathon"` → 41,000-43,000m
   - `"ultra"` → 43,000m+ (no upper limit)
   - `"50k"` → 45,000-55,000m
   - `"100k"` → 90,000-110,000m

2. **Numeric values with units** (with ±10% buffer):
   - `"10km"` → 9,000-11,000m
   - `"5mi"` → 7,239-8,851m
   - `"10000"` → 9,000-11,000m (defaults to meters)
   - Supports: km, mi, m (case-insensitive)

3. **Exact ranges** (no buffer):
   - `"5km:10km"` → 5,000-10,000m
   - `"3mi:6mi"` → 4,828-9,656m
   - `":10km"` → 0-10,000m (open-ended minimum)
   - `"5mi:"` → 8,047m+ (open-ended maximum)

#### Title Filtering

- Case-insensitive substring search in activity names
- Example: `title_contains="tempo"` matches "Tempo Run", "TEMPO", "tempo workout"

#### Race Filtering

- Detects races based on Strava's `workout_type` field:
  - Run races: `workout_type == 1`
  - Ride races: `workout_type == 11`
- `is_race=true` returns only races
- `is_race=false` returns only non-races (training activities)
- Activity types without race detection (e.g., Swim, Walk) are only included in non-race results

### Filter Integration

Filters are available in three tools:

1. **`query_activities`**: Filter activity lists by distance, title, and race status
2. **`analyze_training`**: Analyze only activities matching specified filters
3. **`find_similar_activities`**: Pre-filter candidate activities before similarity matching

All filters use AND logic (activities must match all specified criteria).

### Implementation Notes

- **Client-side filtering**: Strava API doesn't support most of these filters natively, so they're applied after fetching activities
- **Safety limits**: API call limits are reduced when using filters (5 calls vs 10) to prevent excessive requests during pagination
- **Pagination with filters**: Each paginated request re-fetches from the beginning to ensure correct filtering across pages (less efficient but correct)
- **Deep pagination protection**: Maximum 10 pages when using filters to prevent performance issues
- **Cursor validation**: Prevents filter changes mid-pagination to avoid inconsistent results

## Pagination

All list-returning tools support cursor-based pagination to manage response sizes:

### Default Limits
- **Activities**: 10 items (5 with enrichments like streams/laps/zones)
- **Segments**: 10 items
- **Routes**: 10 items
- **Leaderboard**: 50 items (max 200)

### Usage Pattern
```python
# First page
result1 = query_activities(time_range="30d")
data1 = json.loads(result1)

# Check if more pages exist
if data1["pagination"]["has_more"]:
    cursor = data1["pagination"]["cursor"]

    # Next page
    result2 = query_activities(time_range="30d", cursor=cursor)
```

### Pagination Response Structure
```json
{
  "data": {
    "activities": [...]
  },
  "pagination": {
    "cursor": "eyJwYWdl...",  // Use for next request
    "has_more": true,
    "limit": 10,
    "returned": 10
  },
  "metadata": {...}
}
```

### Implementation Notes
- Cursors are opaque Base64-encoded JSON containing page number and filters
- Tools fetch `limit+1` items to detect if more pages exist
- Analysis tools (`analyze_training`, `find_similar_activities`) have reduced internal limits (200-300 max activities)

## Transport Modes

The server supports two transport modes selected via CLI argument (`--transport {stdio,http}`):

### Stdio Mode (Default)
- **Use case**: Claude Desktop, local development
- **Authentication**: Pre-configured tokens in `.env` file (via `strava-mcp-auth` script)
- **Single-user**: One set of credentials per deployment
- **Token storage**: `.env` file (automatically updated on refresh)
- **Setup**: Run `uv run strava-mcp-auth` to generate initial tokens

### HTTP Mode
- **Use case**: ChatGPT integration, AWS Lambda, multi-user deployments
- **Authentication**: OAuth flow per-user (MCP OAuth → Strava OAuth)
- **Multi-user**: Each user gets their own session with separate Strava tokens
- **Token storage**: `SessionStore` (in-memory or DynamoDB)
- **Setup**: Configure OAuth clients in `.env` (e.g., `MCP_OAUTH_CLIENTS`)
- **Entry points**:
  - `uv run strava-mcp --transport http` - CLI with HTTP mode (uses streamable-http transport)
  - `strava_mcp.lambda_handler:handler` - AWS Lambda handler (via Mangum, wraps FastMCP ASGI app)

### Key Differences

| Feature | Stdio Mode | HTTP Mode |
|---------|-----------|-----------|
| **Transport** | stdio (stdin/stdout) | HTTP (SSE or streamable-http) |
| **Users** | Single user | Multi-user |
| **Auth Flow** | Manual token setup | OAuth flow per user |
| **Token Storage** | `.env` file | SessionStore (memory/DynamoDB) |
| **Session Management** | None (static config) | TTL-based sessions (12h default) |
| **Deployment** | Claude Desktop | ChatGPT, Lambda, containers |

## Configuration Files

**.env** - Mode-specific configuration
- **Common**: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`
- **Stdio only**: `STRAVA_ACCESS_TOKEN`, `STRAVA_REFRESH_TOKEN`
- **HTTP only**: `STRAVA_MCP_HOST`, `STRAVA_MCP_PORT`, `STRAVA_MCP_BASE_URL`, `MCP_OAUTH_CLIENTS`

**Note**: Transport mode is selected via CLI argument, not environment variable.

**pyproject.toml** - Project dependencies, scripts, tool configuration (pytest, ruff, pyright)

**.claude/commands/commit.md** - Custom slash command for creating conventional commits

## MCP Integration

### Stdio Mode (Claude Desktop)
```json
{
  "mcpServers": {
    "strava": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/strava-mcp", "strava-mcp"]
    }
  }
}
```

### HTTP Mode (ChatGPT)
1. Deploy server to Lambda (via `lambda_handler.py`) or run locally with `--transport http`
2. Configure `STRAVA_MCP_BASE_URL` to your public endpoint
3. Register ChatGPT client in `MCP_OAUTH_CLIENTS` (auto-included by default)
4. ChatGPT will initiate OAuth flow on first connection

All tools, resources, and prompts are automatically discoverable by the MCP client in both modes.
