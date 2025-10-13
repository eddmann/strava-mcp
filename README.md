# Strava MCP Server

A Model Context Protocol (MCP) server for Strava integration. Access your activities, athlete stats, segments, and routes through Claude and other LLMs.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.3.1-green.svg)](https://modelcontextprotocol.io)

## Overview

This MCP server provides 11 tools to interact with your Strava account, organized into 5 categories:

- Activities (2 tools) - Query and analyze your Strava activities
- Athlete (1 tool) - Access profile, statistics, and training zones
- Segments (3 tools) - Explore and track segment efforts
- Routes (2 tools) - Manage and export routes
- Analysis (3 tools) - Training insights, comparison, and similarity search

Additionally, the server provides:

- **1 MCP Resource** - Athlete profile with stats and zones for ongoing context
- **5 MCP Prompts** - Templates for common queries (training analysis, segment performance, activity analysis, run comparison, training summary)

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

1. OAuth Flow - Authorize the app through your browser
2. Token Storage - OAuth tokens saved to `.env` file
3. Auto-Refresh - Tokens automatically refreshed when expired
4. Persistence - Subsequent runs reuse stored tokens

### Option 1: Using UV

```bash
# Install dependencies
cd strava-mcp
uv sync
```

Then configure credentials using one of these methods:

#### Interactive Setup

```bash
uv run strava-mcp-auth
```

This will display an authorization URL to visit in your browser and save credentials to `.env`.

#### Manual Setup

Create a `.env` file manually:

```bash
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_ACCESS_TOKEN=your_access_token
STRAVA_REFRESH_TOKEN=your_refresh_token
```

### Option 2: Using Docker

```bash
# Pull the image
docker pull ghcr.io/eddmann/strava-mcp:latest
```

Then configure credentials using one of these methods:

#### Interactive Setup

```bash
docker run -it --rm \
  -v "/ABSOLUTE/PATH/TO/strava-mcp.env:/app/.env" \
  ghcr.io/eddmann/strava-mcp:latest \
  python -m strava_mcp.scripts.setup_auth
```

This will display an authorization URL to visit in your browser and save credentials to `strava-mcp.env`.

#### Manual Setup

Create a `strava-mcp.env` file manually in your current directory (see UV manual setup above for format).

### Required OAuth Scopes

The authentication process requests these scopes:

- `profile:read_all` - Read athlete profile and zones
- `activity:read_all` - Read all activity data
- `activity:read` - Read activity summaries
- `profile:write` - Star/unstar segments

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
        "strava-mcp"
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
        "ghcr.io/eddmann/strava-mcp:latest"
      ]
    }
  }
}
```

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
```

### Athlete Profile & Stats

```
"Show my athlete profile with year-to-date stats and training zones"
```

*Note: The athlete profile resource (`strava://athlete/profile`) automatically provides ongoing context.*

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
"Compare my last three 10K runs"
"Find runs similar to my last tempo workout"
```

## Available Tools

### Activities (2 tools)

| Tool                  | Description                                                                  |
| --------------------- | ---------------------------------------------------------------------------- |
| `query-activities`    | Unified query for activities with optional enrichment (laps, zones, streams) |
| `get-activity-social` | Get comments and kudos for an activity                                       |

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

| Tool                      | Description                                                              |
| ------------------------- | ------------------------------------------------------------------------ |
| `analyze-training`        | Analyze training over a time period with aggregated metrics and insights |
| `compare-activities`      | Compare 2-5 activities side-by-side                                      |
| `find-similar-activities` | Find activities similar to a reference activity for progress tracking    |

## MCP Resources

Resources provide ongoing context to the LLM without requiring explicit tool calls:

| Resource                     | Description                                                 |
| ---------------------------- | ----------------------------------------------------------- |
| `strava://athlete/profile`   | Complete athlete profile with recent stats, zones, and gear |

## MCP Prompts

Prompt templates for common queries (accessible via prompt suggestion in Claude):

| Prompt                    | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `analyze-recent-training` | Comprehensive training analysis over a specified period  |
| `segment-performance`     | Detailed segment performance analysis                    |
| `activity-deep-dive`      | Deep dive into a specific activity with all metrics      |
| `compare-recent-runs`     | Compare recent runs to identify trends and improvements  |
| `training-summary`        | Comprehensive training overview with recommendations     |

## License

MIT License - see [LICENSE](LICENSE) file for details

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Strava, Inc. All product names, logos, and brands are property of their respective owners.
