# Strava MCP Server

A Model Context Protocol (MCP) server for Strava integration. Access your activities, athlete stats, segments, and routes through Claude and other LLMs.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.3.1-green.svg)](https://modelcontextprotocol.io)

## Overview

This MCP server provides 18 tools to interact with your Strava account, organised into 4 categories:

- **Activities** (5 tools) - List, filter, and analyse your Strava activities
- **Athlete** (3 tools) - Access profile, statistics, and training zones
- **Segments** (6 tools) - Explore and track segment efforts
- **Routes** (4 tools) - Manage and export routes

## Setup

### Prerequisites

- Python 3.11+ and [uv](https://github.com/astral-sh/uv), OR
- Docker

### Option 1: Using UV

```bash
# Install dependencies
cd my-strava-mcp
uv sync

# Configure credentials
uv run strava-mcp-auth
```

### Option 2: Using Docker

```bash
# Pull the image
docker pull eddmann/strava-mcp:latest
```

## Authentication

### How It Works

1. **Create API App**: Register an application at https://www.strava.com/settings/api
2. **OAuth Flow**: Authorise the app through your browser
3. **Token Storage**: OAuth tokens saved to `.env` file
4. **Auto-Refresh**: Tokens automatically refreshed when expired
5. **Persistence**: Subsequent runs reuse stored tokens

### Configure Credentials

Run interactive setup:

```bash
uv run strava-mcp-auth
```

Or create `.env` file manually:

```bash
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_ACCESS_TOKEN=your_access_token
STRAVA_REFRESH_TOKEN=your_refresh_token
```

**Required OAuth Scopes:**

- `profile:read_all` - Read athlete profile and zones
- `activity:read_all` - Read all activity data
- `activity:read` - Read activity summaries
- `profile:write` - Star/unstar segments

## Claude Desktop Configuration

Add to your configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Using UV

```json
{
  "mcpServers": {
    "strava": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/my-strava-mcp",
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
        "/ABSOLUTE/PATH/TO/my-strava-mcp/.env:/app/.env",
        "eddmann/strava-mcp:latest"
      ]
    }
  }
}
```

## Usage

Ask Claude to interact with your Strava data using natural language:

### Activities

```
"Show me my recent runs"
"Get all my runs from August 2025"
"What was my pace and heart rate for my last tempo run?"
"Show me the heart rate and cadence data for my last interval session"
"What were my kilometre splits for my last long run?"
```

### Athlete Stats

```
"Show my running profile and current weight"
"What are my year-to-date running stats?"
"How many kilometres have I run this month compared to all-time?"
"Show me my heart rate zones"
"What are my current training zones?"
```

### Segments

```
"List my starred running segments"
"Find popular running segments near coordinates 51.5074, -0.1278"
"Show details for segment 229781"
"Star that hill segment I ran yesterday"
"What's my PR on this parkrun segment?"
"Show all my attempts at this segment"
```

### Routes

```
"Show me all my running routes"
"Show details for my regular long run route"
"What's the elevation profile of my hilly 10k route?"
"Export my marathon route to GPX"
"Export my favourite half marathon course to TCX"
```

## Available Tools

### Activities (5 tools)

| Tool                    | Description                                                   |
| ----------------------- | ------------------------------------------------------------- |
| `get-recent-activities` | Get recent activities for the authenticated athlete           |
| `get-all-activities`    | Get all activities with optional filtering by date and type   |
| `get-activity-details`  | Get detailed information about a specific activity            |
| `get-activity-streams`  | Get activity streams (time-series data) for detailed analysis |
| `get-activity-laps`     | Get lap information for a specific activity                   |

### Athlete (3 tools)

| Tool                  | Description                                                        |
| --------------------- | ------------------------------------------------------------------ |
| `get-athlete-profile` | Get the authenticated athlete's profile information                |
| `get-athlete-stats`   | Get statistics for an athlete (recent, year-to-date, and all-time) |
| `get-athlete-zones`   | Get the authenticated athlete's heart rate and power zones         |

### Segments (6 tools)

| Tool                    | Description                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| `list-starred-segments` | List segments starred by the authenticated athlete               |
| `explore-segments`      | Explore segments within geographic bounds                        |
| `get-segment`           | Get detailed information about a specific segment                |
| `star-segment`          | Star or unstar a segment                                         |
| `get-segment-effort`    | Get detailed information about a specific segment effort         |
| `list-segment-efforts`  | List efforts for a specific segment by the authenticated athlete |

### Routes (4 tools)

| Tool                  | Description                                     |
| --------------------- | ----------------------------------------------- |
| `list-athlete-routes` | List routes for an athlete                      |
| `get-route`           | Get detailed information about a specific route |
| `export-route-gpx`    | Export a route as GPX file                      |
| `export-route-tcx`    | Export a route as TCX file                      |

## License

MIT License - see [LICENSE](LICENSE) file for details
