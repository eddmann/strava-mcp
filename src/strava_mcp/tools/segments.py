"""Segment-related tools for Strava MCP server."""

from datetime import datetime
from typing import Annotated

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..formatters import (
    format_date,
    format_datetime,
    format_distance,
    format_duration,
    format_elevation,
    format_pace,
    format_speed,
)


async def list_starred_segments(
    page: Annotated[int, "Page number (default: 1)"] = 1,
    per_page: Annotated[int, "Number of segments per page (default: 30)"] = 30,
) -> str:
    """List segments starred by the authenticated athlete."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            # Get athlete to determine measurement preference
            athlete = await client.get_athlete()
            unit = athlete.measurement_preference or "meters"

            segments = await client.list_starred_segments(page=page, per_page=per_page)

            if not segments:
                return "No starred segments found."

            output = [f"Found {len(segments)} starred segments:\n"]

            for segment in segments:
                output.append(f"• {segment.name}")
                output.append(f"  ID: {segment.id}")
                output.append(f"  Type: {segment.activity_type}")
                output.append(f"  Distance: {format_distance(segment.distance, unit)}")
                output.append(f"  Avg Grade: {segment.average_grade:.1f}%")
                output.append(f"  Max Grade: {segment.maximum_grade:.1f}%")
                output.append(
                    f"  Elevation: {format_elevation(segment.elevation_high - segment.elevation_low, unit)}"
                )
                output.append(f"  Climb Category: {segment.climb_category}")

                if segment.city or segment.state or segment.country:
                    location = ", ".join(
                        filter(None, [segment.city, segment.state, segment.country])
                    )
                    output.append(f"  Location: {location}")

                output.append("")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def explore_segments(
    bounds: Annotated[
        str, "Comma-separated bounds: sw_lat,sw_lng,ne_lat,ne_lng (e.g., '37.7,-122.5,37.8,-122.4')"
    ],
    activity_type: Annotated[str | None, "Activity type filter: 'riding' or 'running'"] = None,
    min_cat: Annotated[int | None, "Minimum climb category (0-5)"] = None,
    max_cat: Annotated[int | None, "Maximum climb category (0-5)"] = None,
) -> str:
    """Explore segments within geographic bounds."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Parse bounds
        bounds_list = [float(x.strip()) for x in bounds.split(",")]
        if len(bounds_list) != 4:
            return "Error: bounds must be 4 comma-separated values: sw_lat,sw_lng,ne_lat,ne_lng"

        # Validate climb category filters with activity type
        if (min_cat is not None or max_cat is not None) and activity_type != "riding":
            return "Error: Climb category filters require activity_type='riding'"

        async with StravaClient(config) as client:
            # Get athlete for measurement preference
            athlete = await client.get_athlete()
            unit = athlete.measurement_preference or "meters"

            result = await client.explore_segments(
                bounds=bounds_list,
                activity_type=activity_type,
                min_cat=min_cat,
                max_cat=max_cat,
            )

            segments = result.get("segments", [])

            if not segments:
                return "No segments found in the specified area."

            output = [f"Found {len(segments)} segments:\n"]

            for seg in segments:
                output.append(f"• {seg.get('name', 'Unnamed')}")
                output.append(f"  ID: {seg.get('id')}")
                output.append(f"  Type: {seg.get('activity_type', 'N/A')}")

                if "distance" in seg:
                    output.append(f"  Distance: {format_distance(seg['distance'], unit)}")

                if "avg_grade" in seg:
                    output.append(f"  Avg Grade: {seg['avg_grade']:.1f}%")

                if "climb_category" in seg:
                    output.append(f"  Climb Category: {seg['climb_category']}")

                if "starred" in seg:
                    output.append(f"  Starred: {'Yes' if seg['starred'] else 'No'}")

                output.append("")

            return "\n".join(output)

    except ValueError as e:
        return f"Error: Invalid bounds format. {str(e)}"
    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_segment(
    segment_id: Annotated[int, "The ID of the segment"],
) -> str:
    """Get detailed information about a specific segment."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            # Get athlete for measurement preference
            athlete = await client.get_athlete()
            unit = athlete.measurement_preference or "meters"

            segment = await client.get_segment(segment_id)

            output = [f"Segment: {segment.name}\n"]
            output.append(f"ID: {segment.id}")
            output.append(f"Activity Type: {segment.activity_type}")
            output.append("")

            output.append("Measurements:")
            output.append(f"  Distance: {format_distance(segment.distance, unit)}")
            output.append(f"  Avg Grade: {segment.average_grade:.1f}%")
            output.append(f"  Max Grade: {segment.maximum_grade:.1f}%")
            output.append(f"  Elevation High: {format_elevation(segment.elevation_high, unit)}")
            output.append(f"  Elevation Low: {format_elevation(segment.elevation_low, unit)}")
            output.append(
                f"  Elevation Gain: {format_elevation(segment.elevation_high - segment.elevation_low, unit)}"
            )
            output.append(f"  Climb Category: {segment.climb_category}")
            output.append("")

            if segment.city or segment.state or segment.country:
                output.append("Location:")
                if segment.city:
                    output.append(f"  City: {segment.city}")
                if segment.state:
                    output.append(f"  State: {segment.state}")
                if segment.country:
                    output.append(f"  Country: {segment.country}")
                output.append("")

            output.append("Popularity:")
            if segment.effort_count:
                output.append(f"  Total Efforts: {segment.effort_count}")
            if segment.athlete_count:
                output.append(f"  Total Athletes: {segment.athlete_count}")
            if segment.star_count:
                output.append(f"  Stars: {segment.star_count}")
            output.append(f"  Starred by you: {'Yes' if segment.starred else 'No'}")
            output.append("")

            if segment.created_at:
                output.append(f"Created: {format_datetime(segment.created_at)}")

            if segment.hazardous:
                output.append("\n⚠️  This segment has been flagged as hazardous")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def star_segment(
    segment_id: Annotated[int, "The ID of the segment"],
    starred: Annotated[bool, "True to star, False to unstar"] = True,
) -> str:
    """Star or unstar a segment."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            segment = await client.star_segment(segment_id, starred)

            action = "starred" if starred else "unstarred"
            return f"Successfully {action} segment: {segment.name} (ID: {segment.id})"

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_segment_effort(
    effort_id: Annotated[int, "The ID of the segment effort"],
) -> str:
    """Get detailed information about a specific segment effort."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            effort = await client.get_segment_effort(effort_id)

            output = [f"Segment Effort: {effort.name}\n"]
            output.append(f"Effort ID: {effort.id}")
            output.append(f"Date: {format_datetime(effort.start_date_local)}")
            output.append("")

            if effort.segment:
                output.append(f"Segment: {effort.segment.name} (ID: {effort.segment.id})")
                output.append(f"Distance: {format_distance(effort.segment.distance)}")
                output.append("")

            output.append("Performance:")
            output.append(f"  Elapsed Time: {format_duration(effort.elapsed_time)}")
            output.append(f"  Moving Time: {format_duration(effort.moving_time)}")

            if effort.distance:
                avg_speed = effort.distance / effort.moving_time if effort.moving_time > 0 else 0
                output.append(f"  Avg Speed: {format_speed(avg_speed)}")
                output.append(f"  Avg Pace: {format_pace(avg_speed)}")

            output.append("")

            if effort.average_heartrate:
                output.append("Heart Rate:")
                output.append(f"  Average: {effort.average_heartrate:.0f} bpm")
                if effort.max_heartrate:
                    output.append(f"  Max: {effort.max_heartrate} bpm")
                output.append("")

            if effort.average_watts:
                output.append("Power:")
                output.append(f"  Average: {effort.average_watts:.0f} W")
                output.append(f"  Device Watts: {'Yes' if effort.device_watts else 'No'}")
                output.append("")

            if effort.average_cadence:
                output.append(f"Cadence: {effort.average_cadence:.0f} rpm\n")

            if effort.kom_rank:
                output.append(f"KOM Rank: {effort.kom_rank}")
            if effort.pr_rank:
                output.append(f"PR Rank: {effort.pr_rank}")

            if effort.activity:
                output.append(f"\nActivity ID: {effort.activity.id}")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def list_segment_efforts(
    segment_id: Annotated[int, "The ID of the segment"],
    start_date: Annotated[str | None, "Start date filter (ISO format: YYYY-MM-DD)"] = None,
    end_date: Annotated[str | None, "End date filter (ISO format: YYYY-MM-DD)"] = None,
    per_page: Annotated[int, "Number of efforts per page (default: 30)"] = 30,
) -> str:
    """List efforts for a specific segment by the authenticated athlete."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        async with StravaClient(config) as client:
            efforts = await client.list_segment_efforts(
                segment_id=segment_id,
                start_date_local=start_dt,
                end_date_local=end_dt,
                per_page=per_page,
            )

            if not efforts:
                return "No efforts found for this segment."

            output = [f"Found {len(efforts)} efforts for segment {segment_id}:\n"]

            for i, effort in enumerate(efforts, 1):
                output.append(f"{i}. {effort.name}")
                output.append(f"   Effort ID: {effort.id}")
                output.append(f"   Date: {format_date(effort.start_date_local)}")
                output.append(f"   Time: {format_duration(effort.moving_time)}")

                if effort.distance:
                    avg_speed = (
                        effort.distance / effort.moving_time if effort.moving_time > 0 else 0
                    )
                    output.append(f"   Avg Speed: {format_speed(avg_speed)}")

                if effort.average_heartrate:
                    output.append(f"   Avg HR: {effort.average_heartrate:.0f} bpm")

                if effort.average_watts:
                    output.append(f"   Avg Power: {effort.average_watts:.0f} W")

                if effort.pr_rank:
                    output.append(f"   PR Rank: {effort.pr_rank}")

                output.append("")

            return "\n".join(output)

    except ValueError as e:
        return f"Error: Invalid date format. Use YYYY-MM-DD format. ({str(e)})"
    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
