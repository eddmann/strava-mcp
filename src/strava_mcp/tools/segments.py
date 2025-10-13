"""Segment-related tools for Strava MCP server.

This module provides segment query tools with structured JSON output.
"""

from typing import Annotated, Literal

from ..auth import load_config, validate_credentials
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
    limit: Annotated[int, "Maximum number of segments to return"] = 30,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
) -> str:
    """Query Strava segments with flexible options.

    This unified tool can:
    - Get a single segment by ID with optional efforts history
    - List starred segments
    - Explore segments in a geographic area

    Returns: JSON string with structure:
    {
        "data": {
            "segment": {...}        // Single segment mode
            OR
            "segments": [...],      // List mode
            "count": N
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
            # Single segment mode
            if segment_id is not None:
                return await _get_single_segment(client, segment_id, include_efforts, unit, limit)

            # Starred segments mode
            if starred_only:
                return await _list_starred_segments(client, limit, unit)

            # Explore segments mode
            if bounds:
                return await _explore_segments(
                    client, bounds, activity_type, min_category, max_category, limit, unit
                )

            # Default: list starred segments
            return await _list_starred_segments(client, limit, unit)

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
        segment_data["athlete_stats"] = {
            "pr_elapsed_time": {
                "seconds": stats.pr_elapsed_time,
                "formatted": f"{stats.pr_elapsed_time // 60}:{stats.pr_elapsed_time % 60:02d}",
            }
            if stats.pr_elapsed_time
            else None,
            "pr_date": stats.pr_date,
            "effort_count": stats.effort_count,
        }

    data = {"segment": segment_data}

    # Add efforts if requested
    if include_efforts:
        efforts = await client.list_segment_efforts(segment_id=segment_id)
        data["efforts"] = [
            {
                "id": effort.id,
                "name": effort.name,
                "elapsed_time": {
                    "seconds": effort.elapsed_time,
                    "formatted": f"{effort.elapsed_time // 60}:{effort.elapsed_time % 60:02d}",
                },
                "start_date": effort.start_date_local,
                "activity_id": effort.activity.id if effort.activity else None,
            }
            for effort in efforts[:limit]
        ]

    metadata = {
        "query_type": "single_segment",
        "segment_id": segment_id,
    }

    if include_efforts:
        metadata["includes"] = ["efforts"]

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _list_starred_segments(
    client: StravaClient, limit: int, unit: MeasurementPreference
) -> str:
    """List starred segments."""
    segments = await client.list_starred_segments(page=1, per_page=limit)

    formatted_segments = []
    for segment in segments[:limit]:
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
        "count": len(formatted_segments),
    }

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _explore_segments(
    client: StravaClient,
    bounds: str,
    activity_type: Literal["riding", "running"] | None,
    min_category: int | None,
    max_category: int | None,
    limit: int,
    unit: MeasurementPreference,
) -> str:
    """Explore segments in a geographic area."""
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
    segments = response.get("segments", [])

    formatted_segments = []
    for segment in segments[:limit]:
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

    metadata = {
        "query_type": "explore_segments",
        "bounds": bounds,
        "count": len(formatted_segments),
    }

    if activity_type:
        metadata["activity_type"] = activity_type
    if min_category is not None:
        metadata["min_category"] = min_category
    if max_category is not None:
        metadata["max_category"] = max_category

    return ResponseBuilder.build_response(data, metadata=metadata)


async def star_segment(
    segment_id: Annotated[int, "Segment ID"],
    starred: Annotated[bool, "True to star, False to unstar"] = True,
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
    config = load_config()

    if not validate_credentials(config):
        return ResponseBuilder.build_error_response(
            "Strava credentials not configured",
            error_type="authentication_required",
            suggestions=["Run 'strava-mcp-auth' to set up authentication"],
        )

    try:
        async with StravaClient(config) as client:
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
    page: Annotated[int, "Page number (1-indexed)"] = 1,
    per_page: Annotated[int, "Entries per page (max 200)"] = 50,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
) -> str:
    """Get leaderboard for a segment with filtering options.

    Returns: JSON string with structure:
    {
        "data": {
            "segment": {
                "id": N,
                "name": "..."
            },
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
        "metadata": {
            "fetched_at": "ISO timestamp",
            "segment_id": N,
            "filters": {...}
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
            leaderboard = await client.get_segment_leaderboard(
                segment_id=segment_id,
                gender=gender,
                age_group=age_group,
                weight_class=weight_class,
                following=following,
                club_id=club_id,
                date_range=date_range,
                page=page,
                per_page=per_page,
            )

            entries = []
            for entry in leaderboard.entries:
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
                        "start_date": entry.start_date_local.isoformat()
                        if entry.start_date_local
                        else None,
                    }
                )

            data = {
                "entries": entries,
                "entry_count": leaderboard.entry_count,
            }

            metadata = {
                "segment_id": segment_id,
                "filters": {},
            }

            if gender:
                metadata["filters"]["gender"] = gender
            if age_group:
                metadata["filters"]["age_group"] = age_group
            if weight_class:
                metadata["filters"]["weight_class"] = weight_class
            if following:
                metadata["filters"]["following"] = following
            if club_id:
                metadata["filters"]["club_id"] = club_id
            if date_range:
                metadata["filters"]["date_range"] = date_range

            metadata["page"] = page
            metadata["per_page"] = per_page

            return ResponseBuilder.build_response(data, metadata=metadata)

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
