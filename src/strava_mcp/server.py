"""Strava MCP Server - Main entry point."""

from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Strava")

# Register middleware
from .middleware import ClientMiddleware

mcp.add_middleware(ClientMiddleware())

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


# MCP Resources - Provide ongoing context
@mcp.resource("strava://athlete/profile")
async def athlete_profile_resource() -> str:
    """Complete athlete profile with stats, zones, and gear for context."""
    from .auth import load_config
    from .client import StravaAPIError, StravaClient
    from .response_builder import ResponseBuilder

    # Load config directly since resources don't go through middleware
    config = load_config()

    try:
        async with StravaClient(config) as client:
            # Get athlete and stats
            athlete = await client.get_athlete()
            if athlete.id is None:
                return ResponseBuilder.build_error_response(
                    "Athlete ID not available",
                    error_type="invalid_data",
                )

            stats = await client.get_athlete_stats(athlete.id)
            zones = await client.get_athlete_zones()

            # Build minimal profile data
            data = {
                "profile": {
                    "id": athlete.id,
                    "name": f"{athlete.firstname} {athlete.lastname}",
                    "location": {
                        "city": athlete.city,
                        "state": athlete.state,
                        "country": athlete.country,
                    },
                },
                "zones": ResponseBuilder.format_zones(zones.model_dump()),
                "statistics": {
                    "recent": {
                        "run": {
                            "count": stats.recent_run_totals.count,
                            "distance_km": round(stats.recent_run_totals.distance / 1000, 1),
                        },
                        "ride": {
                            "count": stats.recent_ride_totals.count,
                            "distance_km": round(stats.recent_ride_totals.distance / 1000, 1),
                        },
                    }
                },
            }

            return ResponseBuilder.build_response(data, metadata={"type": "athlete_profile"})
    except StravaAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")


# MCP Prompts - Templates for common queries
@mcp.prompt()
async def analyze_recent_training(period: str = "30d") -> str:
    """Analyze my Strava training over a time period.

    Args:
        period: Time period to analyze (e.g., "7d", "30d", "90d", "ytd")
    """
    return f"""Analyze my Strava training over the past {period}.

Focus on:
1. Total volume (distance, time, elevation)
2. Training distribution by activity type
3. Intensity distribution (if heart rate data available)
4. Trends compared to previous periods
5. Key insights and recommendations

Use the analyze_training tool with period="{period}" to get comprehensive analysis,
then present the findings in a clear, actionable format."""


@mcp.prompt()
async def segment_performance(segment_id: int) -> str:
    """Analyze my performance on a specific Strava segment.

    Args:
        segment_id: The ID of the segment to analyze
    """
    return f"""Analyze my performance on Strava segment {segment_id}.

Include:
1. Segment details (distance, elevation, grade)
2. My personal best and recent efforts
3. Leaderboard position
4. Trends in my efforts over time
5. Suggestions for improvement

Use query_segments with segment_id={segment_id} and include_efforts=true,
then also get the leaderboard with get_segment_leaderboard."""


@mcp.prompt()
async def activity_deep_dive(activity_id: int) -> str:
    """Get comprehensive analysis of a specific activity.

    Args:
        activity_id: The ID of the activity to analyze
    """
    return f"""Provide a comprehensive analysis of activity {activity_id}.

Include:
1. Basic metrics (distance, time, pace/speed, elevation)
2. Heart rate and power data (if available)
3. Lap-by-lap breakdown
4. Zone distribution
5. Comparison to similar activities
6. Performance insights

Use query_activities with activity_id={activity_id}, include_laps=true,
include_zones=true, and optionally include streams for detailed data.
Then use find_similar_activities to compare with past performances."""


@mcp.prompt()
async def compare_recent_runs() -> str:
    """Compare my recent runs to track progress."""
    return """Compare my most recent runs to identify trends and improvements.

Steps:
1. Use query_activities to get my last 5-10 runs (time_range="30d", activity_type="Run")
2. Extract the activity IDs from the most recent runs
3. Use compare_activities to do side-by-side comparison
4. Highlight improvements in pace, heart rate efficiency, or consistency
5. Provide actionable feedback"""


@mcp.prompt()
async def training_summary() -> str:
    """Get a comprehensive training summary."""
    return """Provide a comprehensive overview of my recent training.

Include:
1. Last 30 days summary using analyze_training(period="30d")
2. Activity breakdown by type
3. Weekly volume trends
4. Intensity distribution
5. Comparison to longer-term averages (90 days)
6. Recommendations for upcoming training

Make the summary actionable and easy to understand."""


def main():
    """Main entry point for the Strava MCP server."""
    # Run the server with stdio transport (default)
    mcp.run()


if __name__ == "__main__":
    main()
