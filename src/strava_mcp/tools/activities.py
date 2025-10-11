"""Activity-related tools for Strava MCP server."""

import json
from datetime import datetime
from typing import Annotated, Literal

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..formatters import (
    calculate_avg,
    calculate_normalized_power,
    format_date,
    format_datetime,
    format_distance,
    format_duration,
    format_elevation,
    format_pace,
    format_speed,
)


async def get_recent_activities(
    page: Annotated[int, "Page number (default: 1)"] = 1,
    per_page: Annotated[int, "Number of activities per page (default: 30, max: 200)"] = 30,
) -> str:
    """Get recent activities for the authenticated athlete."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            activities = await client.get_recent_activities(page=page, per_page=per_page)

            if not activities:
                return "No activities found."

            output = [f"Found {len(activities)} recent activities:\n"]

            for activity in activities:
                output.append(f"• {activity.name}")
                output.append(f"  ID: {activity.id}")
                output.append(f"  Type: {activity.sport_type}")
                output.append(f"  Date: {format_date(activity.start_date_local)}")
                output.append(f"  Distance: {format_distance(activity.distance)}")
                output.append(f"  Duration: {format_duration(activity.moving_time)}")
                output.append("")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_all_activities(
    before: Annotated[
        str | None, "Filter activities before this date (ISO format: YYYY-MM-DD)"
    ] = None,
    after: Annotated[
        str | None, "Filter activities after this date (ISO format: YYYY-MM-DD)"
    ] = None,
    activity_type: Annotated[str | None, "Filter by activity type (e.g., 'Ride', 'Run')"] = None,
    sport_type: Annotated[str | None, "Filter by sport type (e.g., 'MountainBikeRide')"] = None,
    max_activities: Annotated[int | None, "Maximum number of activities to fetch"] = 100,
    max_api_calls: Annotated[int | None, "Maximum number of API calls to make"] = 10,
    per_page: Annotated[int, "Activities per page (default: 30)"] = 30,
) -> str:
    """Get all activities with optional filtering by date and type."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Parse dates
        before_dt = datetime.fromisoformat(before) if before else None
        after_dt = datetime.fromisoformat(after) if after else None

        async with StravaClient(config) as client:
            activities = await client.get_all_activities(
                before=before_dt,
                after=after_dt,
                per_page=per_page,
                max_activities=max_activities,
                max_api_calls=max_api_calls,
            )

            # Apply type filters
            if activity_type:
                activities = [a for a in activities if a.type == activity_type]
            if sport_type:
                activities = [a for a in activities if a.sport_type == sport_type]

            if not activities:
                return "No activities found matching the criteria."

            output = [f"Found {len(activities)} activities:\n"]

            for activity in activities:
                output.append(f"• {activity.name}")
                output.append(f"  ID: {activity.id}")
                output.append(f"  Type: {activity.sport_type}")
                output.append(f"  Date: {format_date(activity.start_date_local)}")
                output.append(f"  Distance: {format_distance(activity.distance)}")
                output.append(f"  Duration: {format_duration(activity.moving_time)}")
                if activity.total_elevation_gain:
                    output.append(f"  Elevation: {format_elevation(activity.total_elevation_gain)}")
                output.append("")

            return "\n".join(output)

    except ValueError as e:
        return f"Error: Invalid date format. Use YYYY-MM-DD format. ({str(e)})"
    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_activity_details(
    activity_id: Annotated[int, "The ID of the activity"],
) -> str:
    """Get detailed information about a specific activity."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            activity = await client.get_activity(activity_id)

            output = [f"Activity: {activity.name}\n"]
            output.append(f"ID: {activity.id}")
            output.append(f"Type: {activity.sport_type}")
            output.append(f"Date: {format_datetime(activity.start_date_local)}")
            output.append(f"Timezone: {activity.timezone}")
            output.append("")

            output.append("Distance & Time:")
            output.append(f"  Distance: {format_distance(activity.distance)}")
            output.append(f"  Moving Time: {format_duration(activity.moving_time)}")
            output.append(f"  Elapsed Time: {format_duration(activity.elapsed_time)}")
            output.append("")

            if activity.average_speed:
                output.append("Speed:")
                output.append(f"  Average: {format_speed(activity.average_speed)}")
                if activity.max_speed:
                    output.append(f"  Max: {format_speed(activity.max_speed)}")
                output.append(f"  Pace: {format_pace(activity.average_speed)}")
                output.append("")

            if activity.total_elevation_gain:
                output.append("Elevation:")
                output.append(f"  Total Gain: {format_elevation(activity.total_elevation_gain)}")
                output.append("")

            if activity.has_heartrate:
                output.append("Heart Rate:")
                if activity.average_heartrate:
                    output.append(f"  Average: {activity.average_heartrate:.0f} bpm")
                if activity.max_heartrate:
                    output.append(f"  Max: {activity.max_heartrate} bpm")
                output.append("")

            if activity.calories:
                output.append(f"Calories: {activity.calories:.0f}")
                output.append("")

            output.append("Engagement:")
            output.append(f"  Kudos: {activity.kudos_count or 0}")
            output.append(f"  Comments: {activity.comment_count or 0}")
            output.append(f"  Achievements: {activity.achievement_count or 0}")
            output.append("")

            if activity.description:
                output.append(f"Description: {activity.description}")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_activity_streams(
    activity_id: Annotated[int, "The ID of the activity"],
    streams: Annotated[
        str | None,
        "Comma-separated stream types (time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth)",
    ] = None,
    resolution: Annotated[Literal["low", "medium", "high"] | None, "Data resolution"] = None,
    max_results: Annotated[int | None, "Limit number of data points returned"] = None,
) -> str:
    """Get activity streams (time-series data) for detailed analysis."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Parse stream types
        stream_list = streams.split(",") if streams else None

        async with StravaClient(config) as client:
            stream_data = await client.get_activity_streams(
                activity_id=activity_id,
                keys=stream_list,
            )

            if not stream_data:
                return "No stream data available for this activity."

            output = [f"Activity {activity_id} Streams:\n"]

            # Process each stream
            for stream_name, stream_info in stream_data.items():
                if isinstance(stream_info, dict) and "data" in stream_info:
                    # Dynamic data from Strava API - runtime type checking
                    data = stream_info["data"]  # type: ignore[reportUnknownVariableType]

                    # Apply max_results limit
                    if max_results and len(data) > max_results:  # type: ignore[reportUnknownArgumentType]
                        data = data[:max_results]  # type: ignore[reportUnknownVariableType]

                    output.append(f"{stream_name.upper()}:")
                    output.append(f"  Data points: {len(data)}")  # type: ignore[reportUnknownArgumentType]

                    # Calculate and display statistics
                    if stream_name not in ["latlng", "moving", "time"]:
                        if isinstance(data[0], (int, float)):
                            output.append(f"  Max: {max(data)}")  # type: ignore[reportUnknownArgumentType]
                            output.append(f"  Min: {min(data)}")  # type: ignore[reportUnknownArgumentType]
                            output.append(f"  Avg: {calculate_avg(data):.1f}")  # type: ignore[reportUnknownArgumentType]

                            # Special calculations
                            if stream_name == "watts":
                                np = calculate_normalized_power(data)  # type: ignore[reportUnknownArgumentType]
                                output.append(f"  Normalized Power: {np}")
                            elif stream_name == "velocity_smooth":
                                max_kmh = max(data) * 3.6  # type: ignore[reportUnknownVariableType, reportUnknownArgumentType]
                                avg_kmh = calculate_avg(data) * 3.6  # type: ignore[reportUnknownArgumentType]
                                output.append(f"  Max Speed: {max_kmh:.1f} km/h")
                                output.append(f"  Avg Speed: {avg_kmh:.1f} km/h")

                    # Show sample data (first 5 points)
                    if max_results and max_results <= 20:
                        output.append(f"  Data: {data}")
                    else:
                        output.append(f"  Sample (first 5): {data[:5]}")

                    output.append("")

            output.append(
                "\nNote: Use max_results parameter to limit data points for detailed viewing."
            )

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_activity_laps(
    activity_id: Annotated[int, "The ID of the activity"],
) -> str:
    """Get lap information for a specific activity."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            laps = await client.get_activity_laps(activity_id)

            if not laps:
                return "No laps found for this activity."

            output = [f"Found {len(laps)} laps for activity {activity_id}:\n"]

            for i, lap in enumerate(laps, 1):
                output.append(f"Lap {i} - {lap.name or 'Unnamed'}")
                output.append(f"  Distance: {format_distance(lap.distance)}")
                output.append(f"  Moving Time: {format_duration(lap.moving_time)}")
                output.append(f"  Elapsed Time: {format_duration(lap.elapsed_time)}")

                if lap.average_speed:
                    output.append(f"  Avg Speed: {format_speed(lap.average_speed)}")
                    output.append(f"  Avg Pace: {format_pace(lap.average_speed)}")

                if lap.max_speed:
                    output.append(f"  Max Speed: {format_speed(lap.max_speed)}")

                if lap.total_elevation_gain:
                    output.append(f"  Elevation Gain: {format_elevation(lap.total_elevation_gain)}")

                if lap.average_heartrate:
                    output.append(f"  Avg HR: {lap.average_heartrate:.0f} bpm")

                if lap.max_heartrate:
                    output.append(f"  Max HR: {lap.max_heartrate} bpm")

                if lap.average_watts:
                    output.append(f"  Avg Power: {lap.average_watts:.0f} W")

                if lap.average_cadence:
                    output.append(f"  Avg Cadence: {lap.average_cadence:.0f} rpm")

                output.append("")

            # Also include raw JSON for advanced use
            output.append("\n--- Raw Lap Data (JSON) ---")
            output.append(json.dumps([lap.model_dump() for lap in laps], indent=2, default=str))

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
