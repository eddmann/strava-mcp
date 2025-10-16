"""Segment-related tools for Strava MCP server.

This module provides segment query tools with structured JSON output.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context

from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder


async def query_segments(
    segment_id: Annotated[int | None, "Get specific segment by ID"] = None,
    starred_only: Annotated[bool, "List only starred segments"] = False,
    bounds: Annotated[
        str | None,
        "Explore segments in area (format: 'sw_lat,sw_lng,ne_lat,ne_lng')",
    ] = None,
    include_efforts: Annotated[
        bool, "Include athlete's efforts on this segment (only with segment_id)"
    ] = False,
    activity_type: Annotated[
        Literal["riding", "running"] | None, "Filter by activity type (for explore)"
    ] = None,
    min_category: Annotated[int | None, "Minimum climb category 0-5 (for explore)"] = None,
    max_category: Annotated[int | None, "Maximum climb category 0-5 (for explore)"] = None,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
    limit: Annotated[str | int, "Max segments per page (1-50, default 10)"] = 10,
    efforts_limit: Annotated[
        str | int, "Max efforts to return when include_efforts=True (1-50, default 10)"
    ] = 10,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Query Strava segments with pagination support.

    This unified tool can:
    - Get a single segment by ID with optional efforts history
    - List starred segments with pagination
    - Explore segments in a geographic area with pagination

    Returns: JSON string with structure:
    {
        "data": {
            "segment": {...}        // Single segment mode
            OR
            "segments": [...],      // List mode (max 50 items)
            "count": N
        },
        "pagination": {             // List mode only
            "cursor": "...",
            "has_more": true,
            "limit": 10,
            "returned": 10
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "query_type": "single_segment" | "starred_segments" | "explore_segments"
        }
    }

    Examples:
        - Get specific segment: query_segments(segment_id=12345)
        - Get with efforts: query_segments(segment_id=12345, include_efforts=True)
        - List starred: query_segments(starred_only=True)
        - Explore area: query_segments(bounds="37.77,-122.45,37.80,-122.40")
        - Paginate results: query_segments(starred_only=True, cursor="eyJwYWdl...")
    """
    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    # Coerce limits to int if passed as string
    if isinstance(limit, str):
        try:
            limit = int(limit)
        except ValueError:
            return ResponseBuilder.build_error_response(
                f"Invalid limit value: '{limit}'. Must be a number between 1 and 50.",
                error_type="validation_error",
            )
    if isinstance(efforts_limit, str):
        try:
            efforts_limit = int(efforts_limit)
        except ValueError:
            return ResponseBuilder.build_error_response(
                f"Invalid efforts_limit value: '{efforts_limit}'. Must be a number between 1 and 50.",
                error_type="validation_error",
            )

    # Validate limits
    if limit < 1 or limit > 50:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 50.",
            error_type="validation_error",
        )
    if efforts_limit < 1 or efforts_limit > 50:
        return ResponseBuilder.build_error_response(
            f"Invalid efforts_limit: {efforts_limit}. Must be between 1 and 50.",
            error_type="validation_error",
        )

    try:
        # Single segment mode
        if segment_id is not None:
            return await _get_single_segment(
                client, segment_id, include_efforts, unit, efforts_limit
            )

        # Starred segments mode
        if starred_only:
            return await _list_starred_segments(client, limit, cursor, unit)

        # Explore segments mode
        if bounds:
            return await _explore_segments(
                client, bounds, activity_type, min_category, max_category, limit, cursor, unit
            )

        # Default: list starred segments
        return await _list_starred_segments(client, limit, cursor, unit)

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
            suggestions = ["Check that the segment ID is correct"]
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


async def _get_single_segment(
    client: StravaClient,
    segment_id: int,
    include_efforts: bool,
    unit: MeasurementPreference,
    limit: int = 30,
) -> str:
    """Get a single segment with optional efforts."""
    segment = await client.get_segment(segment_id)

    segment_data = {
        "id": segment.id,
        "name": segment.name,
        "activity_type": segment.activity_type,
        "distance": {
            "meters": segment.distance,
            "formatted": f"{segment.distance / 1000:.2f} km"
            if unit == "meters"
            else f"{segment.distance * 0.000621371:.2f} mi",
        },
        "average_grade": {
            "percent": segment.average_grade,
            "formatted": f"{segment.average_grade:.1f}%",
        },
        "maximum_grade": {
            "percent": segment.maximum_grade,
            "formatted": f"{segment.maximum_grade:.1f}%",
        },
        "elevation_high": {
            "meters": segment.elevation_high,
            "formatted": f"{segment.elevation_high:.0f} m"
            if unit == "meters"
            else f"{segment.elevation_high * 3.28084:.0f} ft",
        },
        "elevation_low": {
            "meters": segment.elevation_low,
            "formatted": f"{segment.elevation_low:.0f} m"
            if unit == "meters"
            else f"{segment.elevation_low * 3.28084:.0f} ft",
        },
        "climb_category": segment.climb_category,
        "city": segment.city,
        "state": segment.state,
        "country": segment.country,
        "private": segment.private,
        "starred": segment.starred,
    }

    # Athlete stats
    if segment.athlete_segment_stats:
        stats = segment.athlete_segment_stats
        segment_data["athlete_stats"] = {  # type: ignore[assignment]
            "pr_elapsed_time": {
                "seconds": stats.pr_elapsed_time,
                "formatted": f"{stats.pr_elapsed_time // 60}:{stats.pr_elapsed_time % 60:02d}",
            }
            if stats.pr_elapsed_time
            else None,
            "pr_date": ResponseBuilder.format_date_with_day(stats.pr_date)
            if stats.pr_date
            else None,
            "effort_count": stats.effort_count,
        }

    data: dict[str, Any] = {"segment": segment_data}

    # Add efforts if requested
    if include_efforts:
        efforts = await client.list_segment_efforts(segment_id=segment_id)
        data["efforts"] = [  # type: ignore[assignment]
            {
                "id": effort.id,
                "name": effort.name,
                "elapsed_time": {
                    "seconds": effort.elapsed_time,
                    "formatted": f"{effort.elapsed_time // 60}:{effort.elapsed_time % 60:02d}",
                },
                "start_date": ResponseBuilder.format_date_with_day(effort.start_date_local)
                if effort.start_date_local
                else None,
                "activity_id": effort.activity.id if effort.activity else None,
            }
            for effort in efforts[:limit]
        ]

    metadata: dict[str, Any] = {
        "query_type": "single_segment",
        "segment_id": segment_id,
    }

    if include_efforts:
        metadata["includes"] = ["efforts"]  # type: ignore[assignment]

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _list_starred_segments(
    client: StravaClient, limit: int, cursor: str | None, unit: MeasurementPreference
) -> str:
    """List starred segments with pagination."""
    from ..pagination import build_pagination_info, decode_cursor

    # Parse cursor
    current_page = 1
    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            current_page = cursor_data.get("page", 1)
        except ValueError:
            return ResponseBuilder.build_error_response(
                "Invalid pagination cursor",
                error_type="validation_error",
            )

    # Fetch limit+1 to detect if there are more pages
    segments = await client.list_starred_segments(page=current_page, per_page=limit + 1)

    has_more = len(segments) > limit
    segments = segments[:limit]

    formatted_segments: list[dict[str, Any]] = []
    for segment in segments:
        formatted_segments.append(
            {
                "id": segment.id,
                "name": segment.name,
                "activity_type": segment.activity_type,
                "distance": {
                    "meters": segment.distance,
                    "formatted": f"{segment.distance / 1000:.2f} km"
                    if unit == "meters"
                    else f"{segment.distance * 0.000621371:.2f} mi",
                },
                "average_grade": {
                    "percent": segment.average_grade,
                    "formatted": f"{segment.average_grade:.1f}%",
                },
                "climb_category": segment.climb_category,
                "city": segment.city,
                "state": segment.state,
                "country": segment.country,
            }
        )

    data = {
        "segments": formatted_segments,
        "count": len(formatted_segments),
    }

    metadata = {
        "query_type": "starred_segments",
    }

    pagination = build_pagination_info(
        returned_count=len(formatted_segments),
        limit=limit,
        current_page=current_page,
        has_more=has_more,
    )

    return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)


async def _explore_segments(
    client: StravaClient,
    bounds: str,
    activity_type: Literal["riding", "running"] | None,
    min_category: int | None,
    max_category: int | None,
    limit: int,
    cursor: str | None,
    unit: MeasurementPreference,
) -> str:
    """Explore segments in a geographic area with pagination."""
    from ..pagination import build_pagination_info

    # Note: Strava's explore API doesn't support pagination natively,
    # but we paginate the results client-side
    # Parse bounds
    try:
        coords = [float(x.strip()) for x in bounds.split(",")]
        if len(coords) != 4:
            raise ValueError("Bounds must have 4 coordinates")
        sw_lat, sw_lng, ne_lat, ne_lng = coords
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Invalid bounds format: '{bounds}'. Expected: 'sw_lat,sw_lng,ne_lat,ne_lng'"
        ) from e

    response = await client.explore_segments(
        bounds=[sw_lat, sw_lng, ne_lat, ne_lng],
        activity_type=activity_type,
        min_cat=min_category,
        max_cat=max_category,
    )

    # Extract segments list from response
    all_segments = response.get("segments", [])

    # Determine offset from cursor
    offset = 0
    if cursor:
        try:
            from ..pagination import decode_cursor

            cursor_data = decode_cursor(cursor)
            # For explore, we use page to calculate offset
            page = cursor_data.get("page", 1)
            offset = (page - 1) * limit
        except ValueError:
            return ResponseBuilder.build_error_response(
                "Invalid pagination cursor",
                error_type="validation_error",
            )

    # Slice segments for current page
    start_idx = offset
    end_idx = offset + limit
    segments = all_segments[start_idx:end_idx]
    has_more = end_idx < len(all_segments)

    formatted_segments: list[dict[str, Any]] = []
    for segment in segments:
        formatted_segments.append(
            {
                "id": segment["id"],
                "name": segment["name"],
                "climb_category": segment["climb_category"],
                "climb_category_desc": segment["climb_category_desc"],
                "avg_grade": {
                    "percent": segment["avg_grade"],
                    "formatted": f"{segment['avg_grade']:.1f}%",
                },
                "distance": {
                    "meters": segment["distance"],
                    "formatted": f"{segment['distance'] / 1000:.2f} km"
                    if unit == "meters"
                    else f"{segment['distance'] * 0.000621371:.2f} mi",
                },
                "elev_difference": {
                    "meters": segment["elev_difference"],
                    "formatted": f"{segment['elev_difference']:.0f} m"
                    if unit == "meters"
                    else f"{segment['elev_difference'] * 3.28084:.0f} ft",
                },
                "starred": segment["starred"],
            }
        )

    data = {
        "segments": formatted_segments,
        "count": len(formatted_segments),
    }

    metadata: dict[str, Any] = {
        "query_type": "explore_segments",
        "bounds": bounds,
    }

    if activity_type:
        metadata["activity_type"] = activity_type
    if min_category is not None:
        metadata["min_category"] = min_category
    if max_category is not None:
        metadata["max_category"] = max_category

    # Build pagination filters for cursor
    pagination_filters: dict[str, Any] = {
        "bounds": bounds,
    }
    if activity_type:
        pagination_filters["activity_type"] = activity_type

    current_page = (offset // limit) + 1 if limit > 0 else 1
    pagination = build_pagination_info(
        returned_count=len(formatted_segments),
        limit=limit,
        current_page=current_page,
        has_more=has_more,
        filters=pagination_filters,
    )

    return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)


async def star_segment(
    segment_id: Annotated[int, "Segment ID"],
    starred: Annotated[bool, "True to star, False to unstar"] = True,
    ctx: Context | None = None,
) -> str:
    """Star or unstar a segment.

    Returns: JSON string with structure:
    {
        "data": {
            "segment_id": N,
            "starred": true/false,
            "success": true
        },
        "metadata": {
            "fetched_at": "ISO timestamp"
        }
    }
    """
    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    try:
        result = await client.star_segment(segment_id, starred)

        data = {
            "segment_id": segment_id,
            "starred": result.starred,
            "success": True,
        }

        return ResponseBuilder.build_response(data)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the segment ID is correct"]
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


async def get_segment_leaderboard(
    segment_id: Annotated[int, "Segment ID"],
    gender: Annotated[Literal["M", "F"] | None, "Filter by gender ('M' or 'F')"] = None,
    age_group: Annotated[
        Literal["0_19", "20_24", "25_34", "35_44", "45_54", "55_64", "65_plus"] | None,
        "Filter by age group",
    ] = None,
    weight_class: Annotated[
        Literal["0_54", "55_64", "65_74", "75_84", "85_94", "95_plus"] | None,
        "Filter by weight class (kg)",
    ] = None,
    following: Annotated[bool, "Only show athletes you follow"] = False,
    club_id: Annotated[int | None, "Filter by club ID"] = None,
    date_range: Annotated[
        Literal["this_year", "this_month", "this_week", "today"] | None,
        "Filter by date range",
    ] = None,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
    limit: Annotated[str | int, "Max entries per page (1-200, default 50)"] = 50,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Get leaderboard for a segment with pagination support.

    Returns: JSON string with structure:
    {
        "data": {
            "entries": [
                {
                    "rank": N,
                    "athlete_name": "...",
                    "elapsed_time": {...},
                    "start_date": "..."
                }
            ],
            "entry_count": N
        },
        "pagination": {
            "cursor": "...",
            "has_more": true,
            "limit": 50,
            "returned": 50
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "segment_id": N,
            "filters": {...}
        }
    }
    """
    from ..pagination import build_pagination_info, decode_cursor

    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    # Coerce limit to int if passed as string
    if isinstance(limit, str):
        try:
            limit = int(limit)
        except ValueError:
            return ResponseBuilder.build_error_response(
                f"Invalid limit value: '{limit}'. Must be a number between 1 and 200.",
                error_type="validation_error",
            )

    # Validate limit
    if limit < 1 or limit > 200:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 200.",
            error_type="validation_error",
        )

    # Parse cursor
    current_page = 1
    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            current_page = cursor_data.get("page", 1)
        except ValueError:
            return ResponseBuilder.build_error_response(
                "Invalid pagination cursor",
                error_type="validation_error",
            )

    try:
        # Fetch limit+1 to detect if there are more pages
        leaderboard = await client.get_segment_leaderboard(
            segment_id=segment_id,
            gender=gender,
            age_group=age_group,
            weight_class=weight_class,
            following=following,
            club_id=club_id,
            date_range=date_range,
            page=current_page,
            per_page=limit + 1,
        )

        # Check if there are more results
        has_more = len(leaderboard.entries) > limit
        entries_to_return = leaderboard.entries[:limit]

        entries: list[dict[str, Any]] = []
        for entry in entries_to_return:
            entries.append(
                {
                    "rank": entry.rank,
                    "athlete_name": entry.athlete_name,
                    "elapsed_time": {
                        "seconds": entry.elapsed_time,
                        "formatted": f"{entry.elapsed_time // 60}:{entry.elapsed_time % 60:02d}",
                    },
                    "moving_time": {
                        "seconds": entry.moving_time,
                        "formatted": f"{entry.moving_time // 60}:{entry.moving_time % 60:02d}",
                    }
                    if entry.moving_time
                    else None,
                    "start_date": ResponseBuilder.format_date_with_day(entry.start_date_local)
                    if entry.start_date_local
                    else None,
                }
            )

        data: dict[str, Any] = {
            "entries": entries,
            "entry_count": leaderboard.entry_count,
        }

        filters: dict[str, Any] = {}
        if gender:
            filters["gender"] = gender
        if age_group:
            filters["age_group"] = age_group
        if weight_class:
            filters["weight_class"] = weight_class
        if following:
            filters["following"] = following
        if club_id:
            filters["club_id"] = club_id
        if date_range:
            filters["date_range"] = date_range

        metadata: dict[str, Any] = {
            "segment_id": segment_id,
            "filters": filters,
        }

        pagination = build_pagination_info(
            returned_count=len(entries),
            limit=limit,
            current_page=current_page,
            has_more=has_more,
            filters=filters,
        )

        return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the segment ID is correct"]
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
