"""Route-related tools for Strava MCP server.

This module provides route query and export tools with structured JSON output.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context

from ..auth import StravaConfig
from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder


async def query_routes(
    route_id: Annotated[int | None, "Get specific route by ID"] = None,
    cursor: Annotated[str | None, "Pagination cursor from previous response"] = None,
    limit: Annotated[int, "Max routes per page (1-50, default 10)"] = 10,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Query Strava routes with pagination support.

    This unified tool can:
    - Get a single route by ID
    - List all routes for the authenticated athlete with pagination

    Returns: JSON string with structure:
    {
        "data": {
            "route": {...}          // Single route mode
            OR
            "routes": [...],        // List mode (max 50 items)
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
            "query_type": "single_route" | "list_routes"
        }
    }

    Examples:
        - Get specific route: query_routes(route_id=12345)
        - List routes: query_routes()
        - Paginate results: query_routes(cursor="eyJwYWdl...")
    """
    assert ctx is not None
    config: StravaConfig = ctx.get_state("config")

    # Validate limit
    if limit < 1 or limit > 50:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 50.",
            error_type="validation_error",
        )

    try:
        async with StravaClient(config) as client:
            # Single route mode
            if route_id is not None:
                return await _get_single_route(client, route_id, unit)

            # List routes mode
            return await _list_routes(client, limit, cursor, unit)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the route ID is correct and belongs to your account"]
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


async def _get_single_route(
    client: StravaClient, route_id: int, unit: MeasurementPreference
) -> str:
    """Get a single route."""
    route = await client.get_route(route_id)

    route_data = {
        "id": route.id,
        "name": route.name,
        "description": route.description,
        "athlete_id": route.athlete.id if route.athlete else None,
        "distance": {
            "meters": route.distance,
            "formatted": f"{route.distance / 1000:.2f} km"
            if unit == "meters"
            else f"{route.distance * 0.000621371:.2f} mi",
        },
        "elevation_gain": {
            "meters": route.elevation_gain,
            "formatted": f"{route.elevation_gain:.0f} m"
            if unit == "meters"
            else f"{route.elevation_gain * 3.28084:.0f} ft",
        },
        "type": route.type,
        "sub_type": route.sub_type,
        "private": route.private,
        "starred": route.starred,
        "timestamp": route.timestamp,
    }

    # Estimated moving time
    if route.estimated_moving_time:
        route_data["estimated_moving_time"] = {
            "seconds": route.estimated_moving_time,
            "formatted": f"{route.estimated_moving_time // 3600}h {(route.estimated_moving_time % 3600) // 60}m",
        }

    # Segments
    if route.segments:
        route_data["segments"] = [  # type: ignore[assignment]
            {
                "id": seg.id,
                "name": seg.name,
                "distance": {
                    "meters": seg.distance,
                    "formatted": f"{seg.distance / 1000:.2f} km"
                    if unit == "meters"
                    else f"{seg.distance * 0.000621371:.2f} mi",
                },
                "avg_grade": {
                    "percent": seg.average_grade,
                    "formatted": f"{seg.average_grade:.1f}%",
                },
                "climb_category": seg.climb_category,
            }
            for seg in route.segments
        ]

    data: dict[str, Any] = {"route": route_data}

    metadata = {
        "query_type": "single_route",
        "route_id": route_id,
    }

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _list_routes(
    client: StravaClient, limit: int, cursor: str | None, unit: MeasurementPreference
) -> str:
    """List all routes with pagination."""
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
    routes = await client.list_athlete_routes(page=current_page, per_page=limit + 1)

    has_more = len(routes) > limit
    routes = routes[:limit]

    formatted_routes: list[dict[str, Any]] = []
    for route in routes:
        formatted_routes.append(
            {
                "id": route.id,
                "name": route.name,
                "description": route.description,
                "distance": {
                    "meters": route.distance,
                    "formatted": f"{route.distance / 1000:.2f} km"
                    if unit == "meters"
                    else f"{route.distance * 0.000621371:.2f} mi",
                },
                "elevation_gain": {
                    "meters": route.elevation_gain,
                    "formatted": f"{route.elevation_gain:.0f} m"
                    if unit == "meters"
                    else f"{route.elevation_gain * 3.28084:.0f} ft",
                },
                "type": route.type,
                "sub_type": route.sub_type,
                "starred": route.starred,
                "timestamp": route.timestamp,
            }
        )

    data: dict[str, Any] = {
        "routes": formatted_routes,
        "count": len(formatted_routes),
    }

    metadata: dict[str, Any] = {
        "query_type": "list_routes",
    }

    pagination = build_pagination_info(
        returned_count=len(formatted_routes),
        limit=limit,
        current_page=current_page,
        has_more=has_more,
    )

    return ResponseBuilder.build_response(data, metadata=metadata, pagination=pagination)


async def export_route(
    route_id: Annotated[int, "Route ID"],
    format: Annotated[Literal["gpx", "tcx"], "Export format ('gpx' or 'tcx')"] = "gpx",
    ctx: Context | None = None,
) -> str:
    """Export a route to GPX or TCX format.

    Returns: JSON string with structure:
    {
        "data": {
            "route_id": N,
            "format": "gpx" | "tcx",
            "content": "...",      // File content
            "filename": "route_12345.gpx"
        },
        "metadata": {
            "fetched_at": "ISO timestamp"
        }
    }

    Note: The content field contains the raw GPX/TCX XML data.
    """
    assert ctx is not None
    config: StravaConfig = ctx.get_state("config")

    if format not in ["gpx", "tcx"]:
        return ResponseBuilder.build_error_response(
            f"Invalid format: '{format}'. Must be 'gpx' or 'tcx'.",
            error_type="validation_error",
        )

    try:
        async with StravaClient(config) as client:
            if format == "gpx":
                content = await client.export_route_gpx(route_id)
            else:  # tcx
                content = await client.export_route_tcx(route_id)

            data = {
                "route_id": route_id,
                "format": format,
                "content": content,
                "filename": f"route_{route_id}.{format}",
                "size_bytes": len(content.encode("utf-8")),
            }

            metadata = {
                "export_format": format,
                "route_id": route_id,
            }

            return ResponseBuilder.build_response(data, metadata=metadata)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 404:
            error_type = "not_found"
            suggestions = ["Check that the route ID is correct and belongs to your account"]
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
