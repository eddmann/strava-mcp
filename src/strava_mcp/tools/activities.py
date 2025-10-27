"""Activity-related tools for Strava MCP server.

This module provides activity query tools with structured JSON output.
"""

from typing import Annotated, Any

from fastmcp import Context

from ..client import StravaAPIError, StravaClient
from ..models import ActivityType, MeasurementPreference
from ..response_builder import ResponseBuilder
from ..time_utils import TimeRangePreset, get_range_description, parse_time_range


async def query_activities(
    time_range: Annotated[
        TimeRangePreset | str,
        "Time range for activities. Preset: 'recent', '7d', '30d', '90d', 'ytd', "
        "'this-week', 'this-month', or custom range 'YYYY-MM-DD:YYYY-MM-DD'",
    ] = "recent",
    activity_type: Annotated[
        ActivityType | None, "Filter by activity type (e.g., 'Run', 'Ride', 'Swim')"
    ] = None,
    activity_id: Annotated[int | None, "Get specific activity by ID"] = None,
    distance: Annotated[
        str | None,
        "Filter by distance. Formats: race name ('5k', 'marathon'), "
        "numeric with unit ('10km', '5mi', '10000' for meters) with ±10% buffer, "
        "or exact range ('5km:10km', '3mi:6mi'). Units: km, mi, m (defaults to meters)",
    ] = None,
    title_contains: Annotated[
        str | None, "Filter by activity title (case-insensitive substring match)"
    ] = None,
    is_race: Annotated[
        bool | None, "Filter by race status (true=races only, false=non-races only)"
    ] = None,
    include_streams: Annotated[
        str | None,
        "Include stream data (comma-separated: 'time,heartrate,watts,cadence,temp,velocity_smooth')",
    ] = None,
    include_laps: Annotated[bool, "Include lap data"] = False,
    include_zones: Annotated[bool, "Include heart rate and power zones"] = False,
    cursor: Annotated[
        str | None, "Pagination cursor from previous response (for continuing multi-page queries)"
    ] = None,
    limit: Annotated[
        str | int | None,
        "Maximum activities per page (1-50). Default: 10 for basic queries, 5 with enrichments. "
        "Use pagination cursor for large datasets.",
    ] = None,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Query Strava activities with pagination support.

    This unified tool can:
    - Get a single activity by ID with optional enrichment
    - List activities within a time range with filtering and pagination
    - Include streams, laps, and zones in a single call

    Pagination:
    For large time ranges, use pagination to retrieve all activities:
    1. Make initial request without cursor
    2. Check response["pagination"]["has_more"]
    3. Use response["pagination"]["cursor"] for next page

    Returns: JSON string with structure:
    {
        "data": {
            "activity": {...}       // Single activity mode
            OR
            "activities": [...],    // List mode (max 50 items)
            "aggregated": {...}     // Summary metrics
        },
        "pagination": {             // List mode only
            "cursor": "...",        // Use for next page
            "has_more": true,
            "limit": 10,
            "returned": 10
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
        - Paginate large results: query_activities(time_range="ytd", cursor="eyJwYWdl...")
    """
    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    # Coerce limit to int if passed as string
    if limit is not None and isinstance(limit, str):
        try:
            limit = int(limit)
        except ValueError:
            return ResponseBuilder.build_error_response(
                f"Invalid limit value: '{limit}'. Must be a number between 1 and 50.",
                error_type="validation_error",
            )

    # Determine default limit based on enrichments
    if limit is None:
        if include_streams or include_laps or include_zones:
            limit = 5  # Heavy enrichments need smaller pages
        else:
            limit = 10  # Basic queries

    # Validate limit
    if limit < 1 or limit > 50:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 50.",
            error_type="validation_error",
        )

    try:
        # Single activity mode
        if activity_id is not None:
            return await _get_single_activity(
                client,
                activity_id,
                include_streams,
                include_laps,
                include_zones,
                unit,
            )

        # List activities mode
        return await _list_activities(
            client,
            time_range,
            activity_type,
            distance,
            title_contains,
            is_race,
            limit,
            cursor,
            unit,
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
        data["streams"] = streams  # type: ignore[assignment]

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
    distance: str | None,
    title_contains: str | None,
    is_race: bool | None,
    limit: int,
    cursor: str | None,
    unit: MeasurementPreference,
) -> str:
    """List activities within a time range with filtering and pagination."""
    from ..filters import parse_distance
    from ..pagination import decode_cursor

    # Parse cursor to get page and preserved filters
    current_page = 1

    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            current_page = cursor_data.get("page", 1)
            cursor_filters = cursor_data.get("filters", {})

            # Validate that filters haven't changed mid-pagination
            # This prevents confusing results when users change filters between requests
            if cursor_filters.get("activity_type") != activity_type:
                return ResponseBuilder.build_error_response(
                    "Cannot change activity_type filter during pagination. "
                    "Start a new query without cursor to change filters.",
                    error_type="validation_error",
                )
            if cursor_filters.get("distance") != distance:
                return ResponseBuilder.build_error_response(
                    "Cannot change distance filter during pagination. "
                    "Start a new query without cursor to change filters.",
                    error_type="validation_error",
                )
            if cursor_filters.get("title_contains") != title_contains:
                return ResponseBuilder.build_error_response(
                    "Cannot change title_contains filter during pagination. "
                    "Start a new query without cursor to change filters.",
                    error_type="validation_error",
                )
            if cursor_filters.get("is_race") != is_race:
                return ResponseBuilder.build_error_response(
                    "Cannot change is_race filter during pagination. "
                    "Start a new query without cursor to change filters.",
                    error_type="validation_error",
                )
        except ValueError:
            return ResponseBuilder.build_error_response(
                "Invalid pagination cursor",
                error_type="validation_error",
            )

    # Parse distance filter if provided
    distance_min: int | None = None
    distance_max: int | None = None

    if distance:
        try:
            distance_min, distance_max = parse_distance(distance)
        except ValueError as e:
            return ResponseBuilder.build_error_response(
                str(e),
                error_type="validation_error",
            )

    # Parse time range
    start, end = parse_time_range(time_range)

    # Check if we have filters that require client-side filtering
    has_filters = any(
        [activity_type, distance_min, distance_max, title_contains, is_race is not None]
    )

    # Prevent deep pagination with filters due to performance implications
    # (each page re-fetches and re-filters from the beginning)
    MAX_FILTERED_PAGE = 10
    if has_filters and current_page > MAX_FILTERED_PAGE:
        return ResponseBuilder.build_error_response(
            f"Pagination beyond page {MAX_FILTERED_PAGE} is not supported with filters. "
            "Please narrow your time range or remove filters for deeper pagination.",
            error_type="validation_error",
            suggestions=[
                "Narrow your time range (e.g., use '30d' instead of 'ytd')",
                "Remove or relax filters to enable deeper pagination",
                "Export results from first 10 pages and continue with a new time range",
            ],
        )

    # Fetch all filtered activities up to current page to handle client-side filtering correctly
    # This ensures we don't skip filtered results that span across Strava API pages
    # Note: This means page N re-fetches pages 1 through N-1, which is inefficient but correct
    fetch_limit = limit + 1
    max_to_fetch = (
        current_page * limit + 1
    )  # Fetch all pages up to current + 1 for has_more detection

    activities, is_exhausted = await client.get_activities(
        after=start,
        before=end,
        start_page=1,  # Always start from page 1 to get consistent filtering
        max_activities=max_to_fetch,
        activity_type=activity_type,
        distance_min=distance_min,
        distance_max=distance_max,
        title_contains=title_contains,
        is_race=is_race,
    )

    # Calculate offset for current page (1-indexed pages)
    offset = (current_page - 1) * limit
    page_activities = activities[offset : offset + fetch_limit]

    # Check if there are more results
    has_more = len(page_activities) > limit
    page_activities = page_activities[:limit]

    # Build pagination filters (preserve all filters in cursor)
    pagination_filters: dict[str, Any] = {"time_range": time_range}
    if activity_type:
        pagination_filters["activity_type"] = activity_type
    if distance:
        pagination_filters["distance"] = distance
        pagination_filters["distance_min"] = distance_min
        pagination_filters["distance_max"] = distance_max
    if title_contains:
        pagination_filters["title_contains"] = title_contains
    if is_race is not None:
        pagination_filters["is_race"] = is_race

    # Build pagination info - encode next page number in cursor
    from ..pagination import encode_cursor

    next_cursor = None
    if has_more:
        next_cursor = encode_cursor(current_page + 1, pagination_filters)

    pagination = {
        "cursor": next_cursor,
        "has_more": has_more,
        "limit": limit,
        "returned": len(page_activities),
    }

    # Build metadata with filter information
    metadata: dict[str, Any] = {
        "query_type": "activity_list",
        "time_range": get_range_description(time_range),
        "time_range_parsed": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }

    if activity_type:
        metadata["activity_type"] = activity_type
    if distance:
        metadata["distance_filter"] = distance
        metadata["distance_range"] = {
            "min": distance_min,
            "max": distance_max,
        }
    if title_contains:
        metadata["title_filter"] = title_contains
    if is_race is not None:
        metadata["race_filter"] = is_race

    # Add warning if we hit API limits (helps users understand why results might be incomplete)
    if not is_exhausted and has_filters:
        # We hit API safety limit while filtering
        if current_page > 1:
            metadata["warning"] = (
                f"Reached API safety limit on page {current_page}. "
                "Results may be incomplete due to re-fetching for client-side filtering. "
                "Consider narrowing your time range for more complete results."
            )
        elif not page_activities:
            metadata["warning"] = (
                "Could not find enough matching activities within API safety limit (5 calls = ~1000 activities). "
                "Your filters may be too restrictive. Try narrowing the time range or relaxing filters."
            )

    if not page_activities:
        data: dict[str, Any] = {"activities": [], "aggregated": {"count": 0}}
        return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)

    # Format activities
    formatted_activities: list[dict[str, Any]] = [
        ResponseBuilder.format_activity(a.model_dump(), unit) for a in page_activities
    ]

    # Aggregate metrics
    aggregated = ResponseBuilder.aggregate_activities(
        [a.model_dump() for a in page_activities], unit
    )

    data: dict[str, Any] = {
        "activities": formatted_activities,
        "aggregated": aggregated,
    }

    return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)


async def get_activity_social(
    activity_id: Annotated[int, "Activity ID"],
    include_comments: Annotated[bool, "Include comments"] = True,
    include_kudos: Annotated[bool, "Include kudos"] = True,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Get social data (comments and kudos) for an activity.

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
    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    try:
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
                        "name": f"{comment.athlete.firstname} {comment.athlete.lastname}"
                        if comment.athlete
                        else None,
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
