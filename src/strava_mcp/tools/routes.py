"""Route-related tools for Strava MCP server.

This module provides route query and export tools with structured JSON output.
"""

from typing import Annotated, Literal

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder


async def query_routes(
    route_id: Annotated[int | None, "Get specific route by ID"] = None,
    limit: Annotated[int, "Maximum number of routes to return"] = 30,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
) -> str:
    """Query Strava routes.

    This unified tool can:
    - Get a single route by ID
    - List all routes for the authenticated athlete

    Returns: JSON string with structure:
    {
        "data": {
            "route": {...}          // Single route mode
            OR
            "routes": [...],        // List mode
            "count": N
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "query_type": "single_route" | "list_routes"
        }
    }

    Examples:
        - Get specific route: query_routes(route_id=12345)
        - List all routes: query_routes()
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
            # Single route mode
            if route_id is not None:
                return await _get_single_route(client, route_id, unit)

            # List routes mode
            return await _list_routes(client, limit, unit)

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
        route_data["segments"] = [
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

    data = {"route": route_data}

    metadata = {
        "query_type": "single_route",
        "route_id": route_id,
    }

    return ResponseBuilder.build_response(data, metadata=metadata)


async def _list_routes(client: StravaClient, limit: int, unit: MeasurementPreference) -> str:
    """List all routes."""
    routes = await client.list_athlete_routes(page=1, per_page=limit)

    formatted_routes = []
    for route in routes[:limit]:
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

    data = {
        "routes": formatted_routes,
        "count": len(formatted_routes),
    }

    metadata = {
        "query_type": "list_routes",
        "count": len(formatted_routes),
    }

    return ResponseBuilder.build_response(data, metadata=metadata)


async def export_route(
    route_id: Annotated[int, "Route ID"],
    format: Annotated[Literal["gpx", "tcx"], "Export format ('gpx' or 'tcx')"] = "gpx",
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
    config = load_config()

    if not validate_credentials(config):
        return ResponseBuilder.build_error_response(
            "Strava credentials not configured",
            error_type="authentication_required",
            suggestions=["Run 'strava-mcp-auth' to set up authentication"],
        )

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
