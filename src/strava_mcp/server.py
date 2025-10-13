"""Strava MCP Server - Main entry point."""

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Strava")

# Import and register tools
from .tools.activities import get_activity_social, query_activities
from .tools.analysis import analyze_training, compare_activities, find_similar_activities
from .tools.athlete import get_athlete_profile
from .tools.routes import export_route, query_routes
from .tools.segments import get_segment_leaderboard, query_segments, star_segment

# Register activity tools
mcp.tool()(query_activities)
mcp.tool()(get_activity_social)

# Register athlete tools
mcp.tool()(get_athlete_profile)

# Register segment tools
mcp.tool()(query_segments)
mcp.tool()(star_segment)
mcp.tool()(get_segment_leaderboard)

# Register route tools
mcp.tool()(query_routes)
mcp.tool()(export_route)

# Register analysis tools
mcp.tool()(analyze_training)
mcp.tool()(compare_activities)
mcp.tool()(find_similar_activities)


def main():
    """Main entry point for the Strava MCP server."""
    # Run the server with stdio transport (default)
    mcp.run()


if __name__ == "__main__":
    main()
