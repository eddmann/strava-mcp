"""Activity-related tools for Strava MCP server.

This module provides activity query tools with structured JSON output.
"""

from typing import Any, Annotated

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder
from ..time_utils import get_range_description, parse_time_range


async def query_activities(
    time_range: Annotated[
        str,
        "Time range for activities. Options: 'recent', '7d', '30d', '90d', 'ytd', "
        "'this-week', 'this-month', or 'YYYY-MM-DD:YYYY-MM-DD'",
    ] = "recent",
    activity_type: Annotated[
        str | None, "Filter by activity type (e.g., 'Run', 'Ride', 'Swim')"
    ] = None,
    activity_id: Annotated[int | None, "Get specific activity by ID"] = None,
    include_details: Annotated[bool, "Include full activity details"] = True,
    include_streams: Annotated[
        str | None,
        "Include stream data (comma-separated: 'time,heartrate,watts,cadence,temp,velocity_smooth')",
    ] = None,
    include_laps: Annotated[bool, "Include lap data"] = False,
    include_zones: Annotated[bool, "Include heart rate and power zones"] = False,
    limit: Annotated[int, "Maximum number of activities to return (1-200)"] = 30,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
) -> str:
    """Query Strava activities with optional enrichment.

    This unified tool can:
    - Get a single activity by ID with optional enrichment
    - List activities within a time range with filtering
    - Include streams, laps, and zones in a single call

    Returns: JSON string with structure:
    {
        "data": {
            "activity": {...}       // Single activity mode
            OR
            "activities": [...],    // List mode
            "aggregated": {...}     // Summary metrics
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "query_type": "single_activity" | "activity_list",
            "time_range": "...",
            "count": N
        }
    }

    Examples:
        - Get recent activities: query_activities()
        - Get last 7 days: query_activities(time_range="7d")
        - Get specific activity: query_activities(activity_id=12345)
        - Get with laps and zones: query_activities(activity_id=12345, include_laps=True, include_zones=True)
        - Get runs from last month: query_activities(time_range="30d", activity_type="Run")
    """
    config = load_config()

    if not validate_credentials(config):
        return ResponseBuilder.build_error_response(
            "Strava credentials not configured",
            error_type="authentication_required",
            suggestions=["Run 'strava-mcp-auth' to set up authentication"],
        )

    # Validate limit
    if limit < 1 or limit > 200:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 200.",
            error_type="validation_error",
        )

    try:
        async with StravaClient(config) as client:
            # Single activity mode
            if activity_id is not None:
                return await _get_single_activity(
                    client,
                    activity_id,
                    include_details,
                    include_streams,
                    include_laps,
                    include_zones,
                    unit,
                )

            # List activities mode
            return await _list_activities(
                client, time_range, activity_type, include_details, limit, unit
            )

    except ValueError as e:
        return ResponseBuilder.build_error_response(
            str(e),
            error_type="validation_error",
        )
    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the activity ID is correct and belongs to your account"]
        elif e.status_code == 429:
            error_type = "rate_limit"
            suggestions = ["Wait a few minutes before making more requests"]

        return ResponseBuilder.build_error_response(
            e.message,
            error_type=error_type,
            suggestions=suggestions if suggestions else None,
        )
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}",
            error_type="internal_error",
        )


async def _get_single_activity(
    client: StravaClient,
    activity_id: int,
    include_details: bool,
    include_streams: str | None,
    include_laps: bool,
    include_zones: bool,
    unit: MeasurementPreference,
) -> str:
    """Get a single activity with optional enrichment."""
    # Get activity details
    activity = await client.get_activity(activity_id)

    # Format activity
    formatted_activity = ResponseBuilder.format_activity(activity.model_dump(), unit)

    data: dict[str, Any] = {"activity": formatted_activity}

    # Add streams if requested
    if include_streams:
        stream_types = [s.strip() for s in include_streams.split(",")]
        streams = await client.get_activity_streams(activity_id, stream_types)

        # streams is a dict keyed by stream type when key_by_type=True (default)
        data["streams"] = streams

    # Add laps if requested
    if include_laps:
        laps = await client.get_activity_laps(activity_id)
        data["laps"] = [
            ResponseBuilder.format_lap(lap.model_dump(), i + 1, unit) for i, lap in enumerate(laps)
        ]

    # Add zones if requested
    if include_zones:
        zones = await client.get_activity_zones(activity_id)
        if zones:
            data["zones"] = ResponseBuilder.format_zones(zones[0].model_dump())

    includes: list[str] = []
    if include_streams:
        includes.append(f"streams:{include_streams}")
    if include_laps:
        includes.append("laps")
    if include_zones:
        includes.append("zones")

    metadata = {
        "query_type": "single_activity",
        "activity_id": activity_id,
        "includes": includes,
    }

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _list_activities(
    client: StravaClient,
    time_range: str,
    activity_type: str | None,
    include_details: bool,
    limit: int,
    unit: MeasurementPreference,
) -> str:
    """List activities within a time range."""
    # Parse time range
    start, end = parse_time_range(time_range)

    # Get activities
    activities = await client.get_all_activities(
        after=start,
        before=end,
        per_page=min(limit, 200),
        max_activities=limit,
        max_api_calls=10,
    )

    # Filter by activity type if specified
    if activity_type:
        activities = [a for a in activities if a.type == activity_type]

    # Limit results
    activities = activities[:limit]

    if not activities:
        data: dict[str, Any] = {"activities": [], "aggregated": {"count": 0}}
        metadata: dict[str, Any] = {
            "query_type": "activity_list",
            "time_range": get_range_description(time_range),
            "time_range_parsed": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "count": 0,
        }
        if activity_type:
            metadata["activity_type"] = activity_type

        return ResponseBuilder.build_response(data, metadata=metadata)

    # Format activities
    formatted_activities: list[dict[str, Any]] = [
        ResponseBuilder.format_activity(a.model_dump(), unit) for a in activities
    ]

    # Aggregate metrics
    aggregated = ResponseBuilder.aggregate_activities([a.model_dump() for a in activities], unit)

    data: dict[str, Any] = {
        "activities": formatted_activities,
        "aggregated": aggregated,
    }

    metadata = {
        "query_type": "activity_list",
        "time_range": get_range_description(time_range),
        "time_range_parsed": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "count": len(formatted_activities),
    }

    if activity_type:
        metadata["activity_type"] = activity_type

    return ResponseBuilder.build_response(data, metadata=metadata)


async def get_activity_social(
    activity_id: Annotated[int, "Activity ID"],
    include_comments: Annotated[bool, "Include comments"] = True,
    include_kudos: Annotated[bool, "Include kudos"] = True,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
) -> str:
    """Get social data for an activity (comments and kudos).

    Returns: JSON string with structure:
    {
        "data": {
            "activity": {
                "id": ...,
                "name": "..."
            },
            "comments": [...],
            "kudos": [...]
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "activity_id": N
        }
    }
    """
    config = load_config()

    if not validate_credentials(config):
        return ResponseBuilder.build_error_response(
            "Strava credentials not configured",
            error_type="authentication_required",
            suggestions=["Run 'strava-mcp-auth' to set up authentication"],
        )

    try:
        async with StravaClient(config) as client:
            # Get basic activity info
            activity = await client.get_activity(activity_id)

            data: dict[str, Any] = {
                "activity": {
                    "id": activity.id,
                    "name": activity.name,
                    "type": activity.type,
                }
            }

            # Add comments if requested
            if include_comments:
                comments = await client.get_activity_comments(activity_id)
                data["comments"] = [
                    {
                        "id": comment.id,
                        "athlete": {
                            "id": comment.athlete.id if comment.athlete else None,
                            "name": f"{comment.athlete.firstname} {comment.athlete.lastname}" if comment.athlete else None,
                        },
                        "text": comment.text,
                        "created_at": comment.created_at,
                    }
                    for comment in comments
                ]

            # Add kudos if requested
            if include_kudos:
                kudos = await client.get_activity_kudoers(activity_id)
                data["kudos"] = [
                    {
                        "id": kudoer.id,
                        "name": f"{kudoer.firstname} {kudoer.lastname}",
                    }
                    for kudoer in kudos
                ]

            includes: list[str] = []
            if include_comments:
                includes.append(f"comments:{len(data.get('comments', []))}")
            if include_kudos:
                includes.append(f"kudos:{len(data.get('kudos', []))}")

            metadata: dict[str, Any] = {
                "activity_id": activity_id,
                "includes": includes,
            }

            return ResponseBuilder.build_response(data, metadata=metadata)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the activity ID is correct and belongs to your account"]
        elif e.status_code == 429:
            error_type = "rate_limit"
            suggestions = ["Wait a few minutes before making more requests"]

        return ResponseBuilder.build_error_response(
            e.message,
            error_type=error_type,
            suggestions=suggestions if suggestions else None,
        )
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}",
            error_type="internal_error",
        )
