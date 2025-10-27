# Strava MCP Server

A Model Context Protocol (MCP) server for Strava integration. Access your activities, athlete stats, segments, and routes through Claude, ChatGPT, and other LLMs.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

This MCP server provides 11 tools to interact with your Strava account, organized into 5 categories:

- Activities (2 tools) - Query and analyze your Strava activities
- Athlete (1 tool) - Access profile, statistics, and training zones
- Segments (3 tools) - Explore and track segment efforts
- Routes (2 tools) - Manage and export routes
- Analysis (3 tools) - Training insights, comparison, and similarity search

Additionally, the server provides:

- 1 MCP Resource - Athlete profile with stats and zones for ongoing context
- 5 MCP Prompts - Templates for common queries (training analysis, segment performance, activity analysis, run comparison, training summary)

**Deployment Options:**

- **Stdio Mode**: Single-user local deployment (e.g., Claude Desktop, Cursor)
- **HTTP Mode**: Multi-user deployment (e.g., ChatGPT, remote MCP deployment)

## Prerequisites

- Python 3.11+ and [uv](https://github.com/astral-sh/uv), OR
- Docker

## Strava API Application Setup

Before installation, you need to create a Strava API application:

1. Go to https://www.strava.com/settings/api
2. Create a new application with the following settings:
   - Application Name: Your choice (e.g., "My Strava MCP")
   - Category: Your choice (e.g., "Data Importer")
   - Club: Leave blank (optional)
   - Website: Can be anything (e.g., `http://localhost`)
   - **Authorization Callback Domain: Must be `localhost`**
3. After creation, note your Client ID and Client Secret
4. You'll use these credentials during the setup process below

## Installation & Setup

### How Authentication Works

#### Stdio Mode (single-user, pre-configured)

1. OAuth Flow - One-time authorization through browser
2. Token Storage - OAuth tokens saved to `.env` file
3. Auto-Refresh - Tokens automatically refreshed when expired
4. Persistence - Subsequent runs reuse stored tokens

#### HTTP Mode (multi-user, on-demand)

1. OAuth Flow - Per-user authorization on first connection (MCP OAuth → Strava OAuth)
2. Token Storage - OAuth tokens stored in session store (in-memory or DynamoDB)
3. Auto-Refresh - Tokens refreshed automatically per-session
4. Persistence - Sessions expire after 12 hours (configurable)

### Option 1: Using UV

```bash
# Install dependencies
cd strava-mcp
uv sync
```

Then configure credentials:

```bash
uv run strava-mcp-auth
```

This interactive wizard will guide you through configuring authentication for stdio or http transport modes.

### Option 2: Using Docker

```bash
# Pull the image
docker pull ghcr.io/eddmann/strava-mcp:latest
```

Then configure credentials:

```bash
# Create the env file first (Docker will create it as a directory if it doesn't exist)
touch strava-mcp.env

# Run the setup script
docker run -it --rm \
  -v "/ABSOLUTE/PATH/TO/strava-mcp.env:/app/.env" \
  --entrypoint= \
  ghcr.io/eddmann/strava-mcp:latest \
  python -m strava_mcp.scripts.setup_auth
```

This interactive wizard will guide you through configuring authentication for stdio or http transport modes.

### Required OAuth Scopes

The authentication process requests these scopes:

- `profile:read_all` - Read athlete profile and zones
- `activity:read_all` - Read all activity data
- `activity:read` - Read activity summaries
- `profile:write` - Star/unstar segments

## Transport Modes

The server supports two transport modes selected via `--transport` flag (stdio is default, no flag needed):

### Stdio Mode (Default)

Uses standard input/output for communication with a single pre-configured Strava account.

- Authentication: Pre-configured OAuth tokens in `.env` file
- Users: Single user per deployment
- Setup: Run `strava-mcp-auth` to authorize once
- Token Storage: Local `.env` file

### HTTP Mode (Streamable HTTP)

Uses HTTP transport with per-user OAuth flow.

- Authentication: OAuth flow per user (MCP OAuth → Strava OAuth)
- Users: Multi-user support with separate sessions
- Setup: Environment-based configuration
- Token Storage: In-memory or DynamoDB session store

## Claude Desktop Configuration

Add to your configuration file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Using UV

```json
{
  "mcpServers": {
    "strava": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/strava-mcp",
        "strava-mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Using Docker

```json
{
  "mcpServers": {
    "strava": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/ABSOLUTE/PATH/TO/strava-mcp.env:/app/.env",
        "ghcr.io/eddmann/strava-mcp:latest",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

## ChatGPT Integration & HTTP Mode

### Running in HTTP Mode

Start the server in HTTP mode for deploying remote:

```bash
# Using UV
uv run --directory /ABSOLUTE/PATH/TO/strava-mcp strava-mcp --transport http

# Using Docker
docker run -p 8000:8000 --rm \
  -v "/ABSOLUTE/PATH/TO/strava-mcp.env:/app/.env" \
  ghcr.io/eddmann/strava-mcp:latest \
  --transport http
```

Environment variables can be configured using the `strava-mcp-auth` setup wizard (see Installation & Setup above).

### Local Development with ngrok

To test ChatGPT integration locally:

1. **Start the server in HTTP mode**:

   ```bash
   uv run strava-mcp --transport http
   ```

2. **In a separate terminal, expose via ngrok**:

   ```bash
   ngrok http 8000
   ```

3. **Update environment**: Set `STRAVA_MCP_BASE_URL` to your ngrok URL:

   ```bash
   export STRAVA_MCP_BASE_URL=https://abc123.ngrok.io
   ```

   Or add to your `.env` file:

   ```
   STRAVA_MCP_BASE_URL=https://abc123.ngrok.io
   ```

4. **Restart the server** to pick up the new base URL

5. **Configure ChatGPT**: Use the ngrok URL (with `/mcp` path) as your MCP server endpoint

## Usage

Ask Claude to interact with your Strava data using natural language. The server provides tools, a resource, and prompt templates to help you get started.

### Quick Start with MCP Prompts

Use built-in prompt templates for common queries (available via prompt suggestions in Claude):

- `analyze-recent-training` - Analyze my training over the past 30 days
- `segment-performance` - Analyze my performance on a specific segment
- `activity-deep-dive` - Deep dive into a specific activity
- `compare-recent-runs` - Compare my recent runs to track progress
- `training-summary` - Show me a comprehensive training summary

### Activities

```
"Show me my runs from the last 30 days"
"Get my last long run with lap splits and heart rate zones"
"Show me the comments and kudos on my half marathon race"
"Find all my marathon races from this year"
"Show me all 10km runs from the last 90 days"
```

### Athlete Profile & Stats

```
"Show my athlete profile with year-to-date stats and training zones"
```

_Note: The athlete profile resource (`strava://athlete/profile`) automatically provides ongoing context._

### Segments

```
"Show me the Box Hill segment with my effort history"
"Find running segments near Hyde Park"
"Show the leaderboard for my favorite climb segment"
```

### Routes

```
"List my routes"
"Export my Richmond Park route to GPX"
```

### Training Analysis

```
"Analyze my training over the past 30 days"
"Analyze my marathon race performance this year"
"Compare my last three 10K runs"
"Find runs similar to my last tempo workout"
"Show me all my 5k races from the last year"
```

_Note: List-returning tools use cursor-based pagination with default limits (10 items for activities/segments/routes, 50 for leaderboards)._

## Available Tools

### Activities (2 tools)

| Tool                  | Description                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `query-activities`    | Unified query for activities with filtering (distance, title, race status) and optional enrichment (laps, zones, streams) |
| `get-activity-social` | Get comments and kudos for an activity                                                                                    |

### Athlete (1 tool)

| Tool                  | Description                                                                             |
| --------------------- | --------------------------------------------------------------------------------------- |
| `get-athlete-profile` | Get athlete profile with optional statistics (recent, YTD, all-time) and training zones |

### Segments (3 tools)

| Tool                      | Description                                                             |
| ------------------------- | ----------------------------------------------------------------------- |
| `query-segments`          | Unified segment query (by ID, starred, or explore by geographic bounds) |
| `star-segment`            | Star or unstar a segment                                                |
| `get-segment-leaderboard` | Get segment leaderboard with filtering options                          |

### Routes (2 tools)

| Tool           | Description                                               |
| -------------- | --------------------------------------------------------- |
| `query-routes` | Get route details (single route by ID or list all routes) |
| `export-route` | Export a route to GPX or TCX format                       |

### Analysis (3 tools)

| Tool                      | Description                                                                                              |
| ------------------------- | -------------------------------------------------------------------------------------------------------- |
| `analyze-training`        | Analyze training over a time period with filtering (distance, title, race status) and aggregated metrics |
| `compare-activities`      | Compare 2-5 activities side-by-side                                                                      |
| `find-similar-activities` | Find activities similar to a reference activity with pre-filtering options for progress tracking         |

## MCP Resources

Resources provide ongoing context to the LLM without requiring explicit tool calls:

| Resource                   | Description                                                 |
| -------------------------- | ----------------------------------------------------------- |
| `strava://athlete/profile` | Complete athlete profile with recent stats, zones, and gear |

## MCP Prompts

Prompt templates for common queries (accessible via prompt suggestion in Claude):

| Prompt                      | Description                                             |
| --------------------------- | ------------------------------------------------------- |
| `analyze-recent-training`   | Comprehensive training analysis over a specified period |
| `race-performance-analysis` | Analyze race performance for a specific distance        |
| `segment-performance`       | Detailed segment performance analysis                   |
| `activity-deep-dive`        | Deep dive into a specific activity with all metrics     |
| `compare-recent-runs`       | Compare recent runs to identify trends and improvements |
| `training-summary`          | Comprehensive training overview with recommendations    |

## License

MIT License - see [LICENSE](LICENSE) file for details

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Strava, Inc. All product names, logos, and brands are property of their respective owners.
