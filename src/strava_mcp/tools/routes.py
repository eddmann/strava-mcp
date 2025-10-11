"""Route-related tools for Strava MCP server."""

import os
from pathlib import Path
from typing import Annotated

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..formatters import format_distance, format_duration, format_elevation


async def list_athlete_routes(
    athlete_id: Annotated[int | None, "Athlete ID (defaults to authenticated athlete)"] = None,
    page: Annotated[int, "Page number (default: 1)"] = 1,
    per_page: Annotated[int, "Number of routes per page (default: 30)"] = 30,
) -> str:
    """List routes for an athlete."""
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

            routes = await client.list_athlete_routes(
                athlete_id=athlete_id,
                page=page,
                per_page=per_page,
            )

            if not routes:
                return "No routes found."

            output = [f"Found {len(routes)} routes:\n"]

            for route in routes:
                output.append(f"• {route.name}")
                output.append(f"  ID: {route.id}")

                if route.description:
                    output.append(f"  Description: {route.description}")

                output.append(f"  Distance: {format_distance(route.distance, unit)}")
                output.append(f"  Elevation Gain: {format_elevation(route.elevation_gain, unit)}")

                if route.estimated_moving_time:
                    output.append(f"  Est. Time: {format_duration(route.estimated_moving_time)}")

                output.append(f"  Private: {'Yes' if route.private else 'No'}")
                output.append(f"  Starred: {'Yes' if route.starred else 'No'}")

                if route.created_at:
                    output.append(f"  Created: {route.created_at.strftime('%Y-%m-%d')}")

                output.append("")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_route(
    route_id: Annotated[int, "The ID of the route"],
) -> str:
    """Get detailed information about a specific route."""
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

            route = await client.get_route(route_id)

            output = [f"Route: {route.name}\n"]
            output.append(f"ID: {route.id}")

            if route.description:
                output.append(f"Description: {route.description}")

            output.append("")
            output.append("Measurements:")
            output.append(f"  Distance: {format_distance(route.distance, unit)}")
            output.append(f"  Elevation Gain: {format_elevation(route.elevation_gain, unit)}")

            if route.estimated_moving_time:
                output.append(f"  Estimated Time: {format_duration(route.estimated_moving_time)}")

            output.append("")
            output.append("Properties:")
            output.append(f"  Private: {'Yes' if route.private else 'No'}")
            output.append(f"  Starred: {'Yes' if route.starred else 'No'}")

            if route.created_at:
                output.append(f"  Created: {route.created_at.strftime('%Y-%m-%d')}")

            if route.updated_at:
                output.append(f"  Updated: {route.updated_at.strftime('%Y-%m-%d')}")

            if route.segments:
                output.append(f"\nSegments: {len(route.segments)} segments included")

            output.append(
                f"\nTo export this route, use export-route-gpx or export-route-tcx with ID: {route.id}"
            )

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def validate_export_path(export_path: str) -> tuple[bool, str]:
    """
    Validate the export path for route files.

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(export_path)

    # Check if path exists
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Could not create export directory: {str(e)}"

    # Check if it's a directory
    if not path.is_dir():
        return False, f"Export path is not a directory: {export_path}"

    # Check if it's writable
    if not os.access(path, os.W_OK):
        return False, f"Export directory is not writable: {export_path}"

    return True, ""


async def export_route_gpx(
    route_id: Annotated[int, "The ID of the route"],
    filename: Annotated[str | None, "Custom filename (defaults to route_{id}.gpx)"] = None,
) -> str:
    """Export a route as GPX file."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Validate export path
        export_path = config.route_export_path
        is_valid, error_msg = validate_export_path(export_path)

        if not is_valid:
            return f"Error: {error_msg}"

        # Determine filename
        if not filename:
            filename = f"route_{route_id}.gpx"
        elif not filename.endswith(".gpx"):
            filename += ".gpx"

        file_path = Path(export_path) / filename

        async with StravaClient(config) as client:
            # Get route details first
            route = await client.get_route(route_id)

            # Export GPX
            gpx_data = await client.export_route_gpx(route_id)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(gpx_data)

            return (
                f"Successfully exported route '{route.name}' to GPX:\n"
                f"File: {file_path.absolute()}\n"
                f"Size: {len(gpx_data)} bytes"
            )

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def export_route_tcx(
    route_id: Annotated[int, "The ID of the route"],
    filename: Annotated[str | None, "Custom filename (defaults to route_{id}.tcx)"] = None,
) -> str:
    """Export a route as TCX file."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        # Validate export path
        export_path = config.route_export_path
        is_valid, error_msg = validate_export_path(export_path)

        if not is_valid:
            return f"Error: {error_msg}"

        # Determine filename
        if not filename:
            filename = f"route_{route_id}.tcx"
        elif not filename.endswith(".tcx"):
            filename += ".tcx"

        file_path = Path(export_path) / filename

        async with StravaClient(config) as client:
            # Get route details first
            route = await client.get_route(route_id)

            # Export TCX
            tcx_data = await client.export_route_tcx(route_id)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(tcx_data)

            return (
                f"Successfully exported route '{route.name}' to TCX:\n"
                f"File: {file_path.absolute()}\n"
                f"Size: {len(tcx_data)} bytes"
            )

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
