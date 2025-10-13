# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Model Context Protocol (MCP) server that enables LLMs to interact with the Strava API. Built with Python 3.11+ using FastMCP framework. Provides 11 tools organized into 5 categories (Activities, Athlete, Segments, Routes, Analysis), plus 1 MCP resource and 5 MCP prompts.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
uv sync

# Run authentication setup (interactive OAuth flow)
uv run strava-mcp-auth

# Run the MCP server (typically called by Claude Desktop)
uv run strava-mcp
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
- Initializes FastMCP instance
- Registers all tools, resources, and prompts
- Tools are registered by importing functions from `tools/` modules and wrapping them with `@mcp.tool()` decorator
- MCP resources defined with `@mcp.resource()` decorator (provides ongoing context without explicit tool calls)
- MCP prompts defined with `@mcp.prompt()` decorator (templates for common queries)

**client.py** - Strava API client
- Async HTTP client using `httpx`
- Automatic OAuth token refresh on 401 (handled transparently)
- Comprehensive error handling with custom `StravaAPIError` exception
- Methods organized by API category: activities, athlete, segments, routes
- All API responses validated using Pydantic models

**auth.py** - OAuth authentication
- Configuration loaded from `.env` file via `pydantic-settings`
- Token refresh flow handled automatically by client
- Tokens persisted back to `.env` after refresh
- Interactive setup script in `scripts/setup_auth.py`

**models.py** - Pydantic models
- Complete type definitions for all Strava API responses
- Uses forward references for circular dependencies (e.g., `DetailedActivity` → `Lap` → `MetaActivity`)
- Type aliases for enums (ActivityType, MeasurementPreference, Sex, etc.)

**response_builder.py** - Structured JSON output
- All tools return consistent JSON structure: `{"data": {...}, "analysis": {...}, "metadata": {...}}`
- Formatting utilities that provide both raw and human-readable values (e.g., distance in meters + formatted string)
- Error responses follow standard format: `{"error": {"message": "...", "type": "...", "suggestions": [...]}}`

**formatters.py** - Unit conversion and formatting
- Functions for formatting distance, duration, pace, speed, elevation
- Supports both metric (meters) and imperial (feet) preferences
- Used by `response_builder.py` to generate human-readable output

**time_utils.py** - Time range parsing
- Parses time range strings like "7d", "30d", "ytd", "YYYY-MM-DD:YYYY-MM-DD"
- Used by tools that filter activities by date range

### Tool Organization

Tools are organized into 5 modules under `src/strava_mcp/tools/`:

1. **activities.py** - Query activities with optional enrichment (streams, laps, zones), get social data
2. **athlete.py** - Get athlete profile with optional stats and training zones
3. **segments.py** - Query segments (by ID, starred, or explore), star/unstar, get leaderboard
4. **routes.py** - List routes, get route details, export to GPX/TCX
5. **analysis.py** - Training analysis, activity comparison, similarity search

All tools follow a consistent pattern:
- Accept parameters with `Annotated[type, "description"]` for MCP schema generation
- Validate credentials using `validate_credentials(config)`
- Use async context manager for client: `async with StravaClient(config) as client:`
- Return JSON string via `ResponseBuilder.build_response()` or `ResponseBuilder.build_error_response()`
- Handle `StravaAPIError` exceptions with appropriate error messages

### Testing Strategy

**Test fixtures** (`tests/fixtures/`) - Reusable test data for activities, athletes, routes, segments
**Test stubs** (`tests/stubs/`) - Mock Strava API responses using `respx` library
**Test organization** - One test file per tool module (e.g., `test_activity_tools.py`)
**Async testing** - Uses `pytest-asyncio` with `asyncio_mode = "auto"` (configured in pyproject.toml)

When adding tests:
- Use fixtures from `tests/fixtures/` to create realistic test data
- Mock HTTP responses with `respx` in `tests/stubs/strava_api_stub.py`
- Follow naming convention: `test_<function_name>_<scenario>`

### OAuth Flow

1. User runs `uv run strava-mcp-auth`
2. Script opens browser to Strava authorization URL
3. User authorizes app, redirected to localhost callback
4. Script exchanges authorization code for tokens
5. Tokens saved to `.env` file
6. Server loads tokens on startup via `load_config()`
7. Client automatically refreshes tokens when expired (401 response)
8. Refreshed tokens persisted back to `.env` via `update_env_tokens()`

### Key Design Patterns

**Unified query tools** - Single tool handles multiple query patterns (e.g., `query_activities` can get single activity by ID or list activities with filters)

**Structured JSON output** - All tools return consistent JSON structure with raw + formatted values (e.g., distance in meters + "10.5 km")

**Error handling hierarchy** - `StravaAPIError` → `ResponseBuilder.build_error_response()` → JSON with error type and suggestions

**Automatic token refresh** - Client handles token refresh transparently without exposing OAuth details to tools

**Type safety** - Comprehensive Pydantic models for all API responses ensure type safety throughout the codebase

## Configuration Files

**.env** - OAuth tokens and settings (created by `strava-mcp-auth`, automatically updated when tokens refresh)
**pyproject.toml** - Project dependencies, scripts, tool configuration (pytest, ruff, pyright)
**.claude/commands/commit.md** - Custom slash command for creating conventional commits

## MCP Integration

Claude Desktop configuration typically uses:
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

The server communicates via stdio (standard MCP transport). All tools, resources, and prompts are automatically discoverable by the MCP client.
