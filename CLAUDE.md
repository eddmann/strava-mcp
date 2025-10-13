# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides Strava API integration for Claude and other LLMs. It exposes 18 tools organized into 4 categories: Activities, Athlete, Segments, and Routes.

The server uses FastMCP for the MCP implementation and httpx for async HTTP operations. All Strava API responses are validated using Pydantic models.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Run authentication setup (opens browser for OAuth)
uv run strava-mcp-auth
# OR
make auth
```

### Testing
```bash
# Run all tests
uv run pytest
# OR
make test

# Run specific tests by keyword filter
uv run pytest -k activity
# OR
make test/activity

# Run with verbose output
make test/verbose
```

### Linting and Formatting
```bash
# Run all linters (ruff + pyright)
make lint

# Run ruff linter only
uv run ruff check
# OR
make lint/ruff

# Run pyright type checker only
uv run pyright
# OR
make lint/pyright

# Auto-fix and format code
uv run ruff check --fix && uv run ruff format
# OR
make format
```

### Running the Server
```bash
# Run MCP server locally (stdio transport)
uv run strava-mcp
# OR
make run
```

### Docker
```bash
# Build Docker image
make docker/build

# Run Docker container
make docker/run
```

## Architecture

### Core Components

**Server Entry Point** (`src/strava_mcp/server.py`)
- Initializes FastMCP server instance
- Registers all 18 tools from the tools modules
- Main entry point uses stdio transport for MCP communication

**Authentication & Configuration** (`src/strava_mcp/auth.py`)
- `StravaConfig`: Pydantic settings model that loads from `.env`
- OAuth token refresh functionality with automatic `.env` updates
- Required env vars: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_ACCESS_TOKEN`, `STRAVA_REFRESH_TOKEN`

**HTTP Client** (`src/strava_mcp/client.py`)
- `StravaClient`: Async context manager for Strava API requests
- Automatic token refresh on 401 responses
- Custom error handling for 402 (subscription required), 404, 429 (rate limit)
- All API methods return validated Pydantic models

**Data Models** (`src/strava_mcp/models.py`)
- Comprehensive Pydantic models for all Strava API responses
- Key models: `Athlete`, `SummaryActivity`, `DetailedActivity`, `DetailedSegment`, `Route`, `Zones`, `Lap`, `SegmentEffort`
- Uses Literal types for enums (ActivityType, Sex, MeasurementPreference)

**Formatters** (`src/strava_mcp/formatters.py`)
- Utilities for formatting Strava data for display
- Key functions: `format_duration`, `format_distance`, `format_pace`, `format_speed`, `format_elevation`
- Supports both metric and imperial units based on `unit` parameter
- `calculate_normalized_power`: Calculates NP from power data using 30-second rolling average

### Tools Organization

Tools are organized by domain in `src/strava_mcp/tools/`:

**Activities** (`activities.py`)
- `get_recent_activities`: Returns last 30 activities
- `get_all_activities`: Paginated fetching with date/type filtering
- `get_activity_details`: Full activity details including splits, gear, photos
- `get_activity_streams`: Time-series data (heartrate, cadence, watts, etc.)
- `get_activity_laps`: Lap-by-lap breakdown

**Athlete** (`athlete.py`)
- `get_athlete_profile`: Profile info including weight, FTP, bikes/shoes
- `get_athlete_stats`: Recent, YTD, and all-time statistics by activity type
- `get_athlete_zones`: Heart rate and power training zones

**Segments** (`segments.py`)
- `list_starred_segments`: User's starred segments
- `explore_segments`: Find segments in geographic bounds
- `get_segment`: Detailed segment info with athlete stats
- `star_segment`: Star/unstar a segment (requires `profile:write` scope)
- `get_segment_effort`: Details of a specific effort
- `list_segment_efforts`: All efforts for a segment with date filtering

**Routes** (`routes.py`)
- `list_athlete_routes`: User's saved routes
- `get_route`: Route details including elevation, segments
- `export_route_gpx`: Export as GPX file
- `export_route_tcx`: Export as TCX file

### Testing

Tests use pytest with async support (`pytest-asyncio`) and HTTP mocking (`respx`).

**Test Structure** (`tests/`)
- `conftest.py`: Shared fixtures and test configuration
- `fixtures/`: Fixture data for different resource types (activities, athletes, segments, routes)
- `stubs/`: Mock Strava API responses (`strava_api_stub.py`)
- `test_*_tools.py`: Tool tests that mock the Strava API and verify tool outputs

**Key Testing Patterns**
- All tools are tested with mocked API responses using respx
- Fixtures provide realistic Strava API response data
- Tests verify both successful responses and error handling
- Use `pytest -k <filter>` to run specific test subsets

## Important Notes

### OAuth Scopes
The server requires these Strava OAuth scopes:
- `profile:read_all` - Read athlete profile and zones
- `activity:read_all` - Read all activity data
- `activity:read` - Read activity summaries
- `profile:write` - Star/unstar segments

### Token Management
- Tokens are stored in `.env` file
- `StravaClient` automatically refreshes expired tokens on 401 responses
- Refreshed tokens are persisted back to `.env` for subsequent runs

### Error Handling
- 401: Automatic token refresh and retry
- 402: Subscription required (raise clear error message)
- 404: Resource not found
- 429: Rate limit exceeded

### Type Checking
- Pyright runs in "basic" mode with strict checking only for `src/` directory
- Some type stub warnings are disabled (`reportMissingTypeStubs`, etc.)
- Import order in `server.py` is intentionally after FastMCP initialization (ruff E402 ignored)

### Code Style
- Line length: 100 characters (enforced by ruff format)
- Ruff selects: E, F, B, I, UP (errors, pyflakes, bugbear, isort, pyupgrade)
- Unused imports allowed in `__init__.py` files
