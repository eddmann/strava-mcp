"""Athlete-related tools for Strava MCP server."""

import json
from typing import Annotated

from ..auth import load_config, validate_credentials
from ..client import StravaAPIError, StravaClient
from ..formatters import format_distance, format_duration, format_elevation


async def get_athlete_profile() -> str:
    """Get the authenticated athlete's profile information."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            athlete = await client.get_athlete()

            output = [f"Athlete Profile: {athlete.firstname} {athlete.lastname}\n"]
            output.append(f"ID: {athlete.id}")

            if athlete.username:
                output.append(f"Username: {athlete.username}")

            if athlete.bio:
                output.append(f"Bio: {athlete.bio}")

            output.append("")
            output.append("Location:")
            if athlete.city:
                output.append(f"  City: {athlete.city}")
            if athlete.state:
                output.append(f"  State: {athlete.state}")
            if athlete.country:
                output.append(f"  Country: {athlete.country}")

            output.append("")
            output.append("Account:")
            output.append(f"  Premium: {'Yes' if athlete.premium else 'No'}")
            output.append(f"  Summit: {'Yes' if athlete.summit else 'No'}")

            if athlete.measurement_preference:
                output.append(f"  Measurement: {athlete.measurement_preference}")

            if athlete.weight:
                output.append(f"  Weight: {athlete.weight} kg")

            if athlete.ftp:
                output.append(f"  FTP: {athlete.ftp} W")

            if athlete.created_at:
                output.append(f"  Member since: {athlete.created_at.strftime('%Y-%m-%d')}")

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_athlete_stats(
    athlete_id: Annotated[int | None, "Athlete ID (defaults to authenticated athlete)"] = None,
) -> str:
    """Get statistics for an athlete (recent, year-to-date, and all-time)."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            # If no athlete_id provided, get current athlete's ID
            if athlete_id is None:
                athlete = await client.get_athlete()
                athlete_id = athlete.id

            stats = await client.get_athlete_stats(athlete_id)
            unit = config.strava_measurement_preference

            output = [f"Athlete Stats (ID: {athlete_id})\n"]

            # Recent totals (last 4 weeks)
            output.append("=== RECENT (Last 4 Weeks) ===\n")

            output.append("Ride:")
            output.append(f"  Count: {stats.recent_ride_totals.count}")
            output.append(f"  Distance: {format_distance(stats.recent_ride_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.recent_ride_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.recent_ride_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Run:")
            output.append(f"  Count: {stats.recent_run_totals.count}")
            output.append(f"  Distance: {format_distance(stats.recent_run_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.recent_run_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.recent_run_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Swim:")
            output.append(f"  Count: {stats.recent_swim_totals.count}")
            output.append(f"  Distance: {format_distance(stats.recent_swim_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.recent_swim_totals.moving_time)}")
            output.append("")

            # Year to date totals
            output.append("=== YEAR TO DATE ===\n")

            output.append("Ride:")
            output.append(f"  Count: {stats.ytd_ride_totals.count}")
            output.append(f"  Distance: {format_distance(stats.ytd_ride_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.ytd_ride_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.ytd_ride_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Run:")
            output.append(f"  Count: {stats.ytd_run_totals.count}")
            output.append(f"  Distance: {format_distance(stats.ytd_run_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.ytd_run_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.ytd_run_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Swim:")
            output.append(f"  Count: {stats.ytd_swim_totals.count}")
            output.append(f"  Distance: {format_distance(stats.ytd_swim_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.ytd_swim_totals.moving_time)}")
            output.append("")

            # All time totals
            output.append("=== ALL TIME ===\n")

            output.append("Ride:")
            output.append(f"  Count: {stats.all_ride_totals.count}")
            output.append(f"  Distance: {format_distance(stats.all_ride_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.all_ride_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.all_ride_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Run:")
            output.append(f"  Count: {stats.all_run_totals.count}")
            output.append(f"  Distance: {format_distance(stats.all_run_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.all_run_totals.moving_time)}")
            output.append(
                f"  Elevation: {format_elevation(stats.all_run_totals.elevation_gain, unit)}"
            )
            output.append("")

            output.append("Swim:")
            output.append(f"  Count: {stats.all_swim_totals.count}")
            output.append(f"  Distance: {format_distance(stats.all_swim_totals.distance, unit)}")
            output.append(f"  Time: {format_duration(stats.all_swim_totals.moving_time)}")
            output.append("")

            # Personal bests
            if stats.biggest_ride_distance:
                output.append(f"Biggest Ride: {format_distance(stats.biggest_ride_distance, unit)}")
            if stats.biggest_climb_elevation_gain:
                output.append(
                    f"Biggest Climb: {format_elevation(stats.biggest_climb_elevation_gain, unit)}"
                )

            return "\n".join(output)

    except StravaAPIError as e:
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def get_athlete_zones() -> str:
    """Get the authenticated athlete's heart rate and power zones."""
    config = load_config()

    if not validate_credentials(config):
        return (
            "Error: Strava credentials not configured. "
            "Please run 'strava-mcp-auth' to set up authentication."
        )

    try:
        async with StravaClient(config) as client:
            zones = await client.get_athlete_zones()

            output = ["Athlete Training Zones\n"]

            # Heart rate zones
            if zones.heart_rate:
                output.append("=== HEART RATE ZONES ===")
                output.append(f"Custom Zones: {'Yes' if zones.heart_rate.custom_zones else 'No'}")
                output.append("")

                for i, zone in enumerate(zones.heart_rate.zones, 1):
                    min_hr = zone.min if zone.min is not None else "N/A"
                    max_hr = zone.max if zone.max is not None else "N/A"
                    output.append(f"Zone {i}: {min_hr} - {max_hr} bpm")

                output.append("")

            # Power zones
            if zones.power:
                output.append("=== POWER ZONES ===")
                output.append("")

                for i, zone in enumerate(zones.power.zones, 1):
                    min_power = zone.min if zone.min is not None else "N/A"
                    max_power = zone.max if zone.max is not None else "N/A"
                    output.append(f"Zone {i}: {min_power} - {max_power} W")

                output.append("")

            if not zones.heart_rate and not zones.power:
                return "No training zones configured for this athlete."

            # Include raw JSON for reference
            output.append("\n--- Raw Zone Data (JSON) ---")
            output.append(json.dumps(zones.model_dump(), indent=2, default=str))

            return "\n".join(output)

    except StravaAPIError as e:
        if e.status_code == 403:
            return (
                "Error: Access denied. The 'profile:read_all' scope is required to access training zones. "
                "Please re-run 'strava-mcp-auth' to grant the necessary permissions."
            )
        return f"Error: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
