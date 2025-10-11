"""Strava MCP Server - Main entry point."""

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Strava")

# Import and register all tools
from .tools.activities import (
    get_activity_details,
    get_activity_laps,
    get_activity_streams,
    get_all_activities,
    get_recent_activities,
)
from .tools.athlete import get_athlete_profile, get_athlete_stats, get_athlete_zones
from .tools.routes import (
    export_route_gpx,
    export_route_tcx,
    get_route,
    list_athlete_routes,
)
from .tools.segments import (
    explore_segments,
    get_segment,
    get_segment_effort,
    list_segment_efforts,
    list_starred_segments,
    star_segment,
)

# Register activity tools
mcp.tool()(get_recent_activities)
mcp.tool()(get_all_activities)
mcp.tool()(get_activity_details)
mcp.tool()(get_activity_streams)
mcp.tool()(get_activity_laps)

# Register athlete tools
mcp.tool()(get_athlete_profile)
mcp.tool()(get_athlete_stats)
mcp.tool()(get_athlete_zones)

# Register segment tools
mcp.tool()(list_starred_segments)
mcp.tool()(explore_segments)
mcp.tool()(get_segment)
mcp.tool()(star_segment)
mcp.tool()(get_segment_effort)
mcp.tool()(list_segment_efforts)

# Register route tools
mcp.tool()(list_athlete_routes)
mcp.tool()(get_route)
mcp.tool()(export_route_gpx)
mcp.tool()(export_route_tcx)


def main():
    """Main entry point for the Strava MCP server."""
    # Run the server with stdio transport (default)
    mcp.run()


if __name__ == "__main__":
    main()
