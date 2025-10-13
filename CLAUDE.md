# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides Strava API integration for Claude and other LLMs. The server features structured JSON output and intelligent analysis capabilities.

**Key Features:**

- **Focused tools**: 11 tools organized by domain
- **Structured JSON output**: All tools return machine-readable JSON with both raw and formatted values
- **Analysis tools**: Training insights, activity comparison, and similarity search capabilities
- **Both raw and formatted values**: JSON includes both `meters: 10500` and `formatted: "10.5 km"`

The server uses FastMCP for the MCP implementation and httpx for async HTTP operations. All Strava API responses are validated using Pydantic models and formatted with structured JSON output.

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
- Registers all 11 tools
- Registers 3 MCP resources for ongoing context
- Registers 5 MCP prompts for common queries
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

**Response Builder** (`src/strava_mcp/response_builder.py`)

- Utilities for building structured JSON responses
- `ResponseBuilder.build_response()`: Standard response structure with data, analysis, metadata
- Format functions for activities, laps, zones with both raw and formatted values
- Error response builder with suggestions
- All responses include timestamps and query metadata

**Time Utilities** (`src/strava_mcp/time_utils.py`)

- `parse_time_range()`: Parse flexible time range strings ("7d", "ytd", "YYYY-MM-DD:YYYY-MM-DD")
- Supports: "recent", "7d", "30d", "90d", "ytd", "this-week", "this-month", custom ranges
- Comprehensive validation and error messages

**Formatters** (`src/strava_mcp/formatters.py`)

- Utilities for formatting Strava data for display
- Key functions: `format_duration`, `format_distance`, `format_pace`, `format_speed`, `format_elevation`
- Supports both metric and imperial units based on `unit` parameter
- `calculate_normalized_power`: Calculates NP from power data using 30-second rolling average

### Tools Organization

All tools return structured JSON with this format:

```json
{
  "data": {
    "distance": {
      "meters": 10500, // Raw value for computation
      "formatted": "10.5 km" // Human-readable string
    }
  },
  "analysis": {
    // Optional insights
    "insights": []
  },
  "metadata": {
    // Query context
    "fetched_at": "ISO timestamp",
    "query_type": "..."
  }
}
```

Tools are organized by domain in `src/strava_mcp/tools/`:

**Activities** (`activities.py`) - **2 tools**

- `query_activities`: Unified tool for listing/filtering/getting activities with optional enrichment
  - Single activity by ID or list with filtering
  - Flexible time range parsing ("recent", "7d", "30d", "ytd", "this-week", custom range)
  - Optional includes: laps, zones, streams
  - Returns JSON with aggregated metrics
- `get_activity_social`: Comments and kudos for an activity

**Athlete** (`athlete.py`) - **1 tool**

- `get_athlete_profile`: Comprehensive profile with optional stats and zones
  - Profile information (name, location, weight, FTP, gear)
  - Optional statistics (recent, YTD, all-time)
  - Optional training zones (HR and power)
  - Returns JSON with structured breakdown

**Segments** (`segments.py`) - **3 tools**

- `query_segments`: Unified segment query tool
  - Single segment by ID with optional efforts history
  - List starred segments
  - Explore segments in geographic area
  - Returns JSON with segment details and personal stats
- `star_segment`: Star/unstar a segment (write operation)
- `get_segment_leaderboard`: Leaderboard with filtering options

**Routes** (`routes.py`) - **2 tools**

- `query_routes`: Get route(s) details
  - Single route by ID
  - List all routes
  - Returns JSON with route details
- `export_route`: Export route to GPX or TCX
  - Single tool with format parameter
  - Returns JSON with file content and metadata

**Analysis** (`analysis.py`) - **3 tools**

- `analyze_training`: Training analysis over a period
  - Aggregated metrics (distance, time, elevation)
  - Weekly breakdown and trends
  - Activity type distribution
  - Automated insights
- `compare_activities`: Side-by-side activity comparison
  - Compare 2-5 activities
  - Metrics comparison (distance, time, pace, HR, power)
  - Difference highlights and insights
- `find_similar_activities`: Find activities similar to a reference
  - Similarity scoring based on type, distance, elevation, duration
  - Returns ranked list of similar activities
  - Useful for progress tracking

### JSON Output Format

All tools return structured JSON with this format:

```json
{
  "data": {
    // Main data payload with nested structure
    // Both raw values and formatted strings included
  },
  "analysis": {
    // Optional insights and computed metrics
  },
  "metadata": {
    // Query metadata, timestamps, includes
    "fetched_at": "2025-01-15T12:00:00Z"
  }
}
```

**Benefits:**

- LLMs can easily extract specific fields
- Both machine-readable and human-friendly
- Enables computational analysis
- Consistent structure across all tools

### MCP Resources

The server provides 3 resources for ongoing context:

- **`strava://athlete/profile`** - Current athlete profile with zones and basic info
- **`strava://athlete/stats`** - Athlete statistics summary (recent, YTD, all-time)
- **`strava://activities/recent`** - Last 20 activities for context

These resources are automatically available to the LLM without explicit tool calls, providing continuous context about the athlete's profile, training zones, and recent activity history.

### MCP Prompts

The server provides 5 prompt templates for common queries:

- **`analyze_recent_training`** - Analyze training over a time period (default: 30 days)
- **`segment_performance`** - Analyze performance on a specific segment
- **`activity_deep_dive`** - Comprehensive analysis of a specific activity
- **`compare_recent_runs`** - Compare recent runs to track progress
- **`training_summary`** - Comprehensive training overview

These prompts guide the LLM on how to effectively use the tools to answer common questions, improving discoverability and consistency.

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
- All tools return structured JSON errors with suggestions

### Type Checking

- Pyright runs in "basic" mode with strict checking only for `src/` directory
- Some type stub warnings are disabled (`reportMissingTypeStubs`, etc.)
- Some "Unknown" type warnings from dynamic Strava API data are expected
- Import order in `server.py` is intentionally after FastMCP initialization (ruff E402 ignored)

### Code Style

- Line length: 100 characters (enforced by ruff format)
- Ruff selects: E, F, B, I, UP (errors, pyflakes, bugbear, isort, pyupgrade)
- Unused imports allowed in `__init__.py` files

## Tool Summary

### Total: 11 tools

**Activities (2)**:

- `query_activities` - Unified activity query with optional enrichment
- `get_activity_social` - Comments and kudos

**Athlete (1)**:

- `get_athlete_profile` - Profile with optional stats and zones

**Segments (3)**:

- `query_segments` - Unified segment query
- `star_segment` - Star/unstar segments
- `get_segment_leaderboard` - Leaderboard with filters

**Routes (2)**:

- `query_routes` - Get route(s)
- `export_route` - Export to GPX/TCX

**Analysis (3)**:

- `analyze_training` - Training analysis over time
- `compare_activities` - Side-by-side comparison
- `find_similar_activities` - Progress tracking
