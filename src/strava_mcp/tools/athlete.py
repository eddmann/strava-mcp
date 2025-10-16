"""Athlete-related tools for Strava MCP server.

This module provides athlete profile tools with structured JSON output.
"""

from typing import Annotated, Any, Literal

from fastmcp import Context

from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder


async def get_athlete_profile(
    include_stats: Annotated[bool, "Include athlete statistics"] = True,
    include_zones: Annotated[bool, "Include training zones (HR and power)"] = True,
    stats_period: Annotated[
        Literal["recent", "ytd", "all"],
        "Statistics period: 'recent' (last 4 weeks), 'ytd' (year to date), or 'all' (all time)",
    ] = "all",
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Get comprehensive athlete profile with optional stats and zones.

    This unified tool provides:
    - Basic profile (name, location, weight, FTP, gear)
    - Optional statistics (recent, YTD, all-time)
    - Optional training zones (heart rate and power)

    All in a single API call with structured JSON output.

    Returns: JSON string with structure:
    {
        "data": {
            "profile": {
                "id": ...,
                "name": "...",
                "location": "...",
                "weight": {...},
                "ftp": ...,
                "bikes": [...],
                "shoes": [...]
            },
            "statistics": {
                "recent": {...},
                "ytd": {...},
                "all_time": {...}
            },
            "zones": {
                "heart_rate": {...},
                "power": {...}
            }
        },
        "metadata": {
            "fetched_at": "ISO timestamp",
            "includes": [...]
        }
    }

    Examples:
        - Get full profile: get_athlete_profile()
        - Get profile only: get_athlete_profile(include_stats=False, include_zones=False)
        - Get recent stats: get_athlete_profile(stats_period="recent")
    """
    assert ctx is not None
    client: StravaClient = ctx.get_state("client")

    try:
        # Get athlete profile
        athlete = await client.get_athlete()

        # Build profile data
        profile_data = {
            "id": athlete.id,
            "name": f"{athlete.firstname} {athlete.lastname}",
            "username": athlete.username,
            "location": {
                "city": athlete.city,
                "state": athlete.state,
                "country": athlete.country,
            },
            "sex": athlete.sex,
            "created_at": athlete.created_at,
            "updated_at": athlete.updated_at,
        }

        # Weight
        if athlete.weight:
            profile_data["weight"] = {  # type: ignore[assignment]
                "kg": athlete.weight,
                "formatted": f"{athlete.weight} kg"
                if unit == "meters"
                else f"{athlete.weight * 2.20462:.1f} lbs",
            }

        # FTP
        if athlete.ftp:
            profile_data["ftp"] = {"watts": athlete.ftp}  # type: ignore[assignment]

        # Measurement preference
        profile_data["measurement_preference"] = athlete.measurement_preference

        # Profile photo
        if athlete.profile:
            profile_data["profile_photo"] = athlete.profile

        # Bikes
        if athlete.bikes:
            profile_data["bikes"] = [  # type: ignore[assignment]
                {
                    "id": bike.id,
                    "name": bike.name,
                    "primary": bike.primary,
                    "distance": {
                        "meters": bike.distance if bike.distance else 0,
                        "formatted": f"{(bike.distance if bike.distance else 0) / 1000:.1f} km"
                        if unit == "meters"
                        else f"{(bike.distance if bike.distance else 0) * 0.000621371:.1f} mi",
                    },
                }
                for bike in athlete.bikes
            ]

        # Shoes
        if athlete.shoes:
            profile_data["shoes"] = [  # type: ignore[assignment]
                {
                    "id": shoe.id,
                    "name": shoe.name,
                    "primary": shoe.primary,
                    "distance": {
                        "meters": shoe.distance if shoe.distance else 0,
                        "formatted": f"{(shoe.distance if shoe.distance else 0) / 1000:.1f} km"
                        if unit == "meters"
                        else f"{(shoe.distance if shoe.distance else 0) * 0.000621371:.1f} mi",
                    },
                }
                for shoe in athlete.shoes
            ]

        data: dict[str, Any] = {"profile": profile_data}
        metadata: dict[str, list[str]] = {"includes": []}

        # Add statistics if requested
        if include_stats:
            if athlete.id is None:
                return ResponseBuilder.build_error_response(
                    "Athlete ID is required to fetch statistics",
                    error_type="invalid_data",
                )
            stats = await client.get_athlete_stats(athlete.id)

            statistics = {}

            # Recent stats (last 4 weeks)
            if stats_period in ["recent", "all"]:
                recent_run = stats.recent_run_totals
                recent_ride = stats.recent_ride_totals
                recent_swim = stats.recent_swim_totals

                statistics["recent"] = {
                    "description": "Last 4 weeks",
                    "run": {
                        "count": recent_run.count,
                        "distance": {
                            "meters": recent_run.distance,
                            "formatted": f"{recent_run.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{recent_run.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": recent_run.moving_time,
                            "formatted": f"{recent_run.moving_time // 3600}h {(recent_run.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": recent_run.elevation_gain,
                            "formatted": f"{recent_run.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{recent_run.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "ride": {
                        "count": recent_ride.count,
                        "distance": {
                            "meters": recent_ride.distance,
                            "formatted": f"{recent_ride.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{recent_ride.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": recent_ride.moving_time,
                            "formatted": f"{recent_ride.moving_time // 3600}h {(recent_ride.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": recent_ride.elevation_gain,
                            "formatted": f"{recent_ride.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{recent_ride.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "swim": {
                        "count": recent_swim.count,
                        "distance": {
                            "meters": recent_swim.distance,
                            "formatted": f"{recent_swim.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{recent_swim.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": recent_swim.moving_time,
                            "formatted": f"{recent_swim.moving_time // 3600}h {(recent_swim.moving_time % 3600) // 60}m",
                        },
                    },
                }

            # YTD stats
            if stats_period in ["ytd", "all"]:
                ytd_run = stats.ytd_run_totals
                ytd_ride = stats.ytd_ride_totals
                ytd_swim = stats.ytd_swim_totals

                statistics["ytd"] = {
                    "description": "Year to date",
                    "run": {
                        "count": ytd_run.count,
                        "distance": {
                            "meters": ytd_run.distance,
                            "formatted": f"{ytd_run.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{ytd_run.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": ytd_run.moving_time,
                            "formatted": f"{ytd_run.moving_time // 3600}h {(ytd_run.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": ytd_run.elevation_gain,
                            "formatted": f"{ytd_run.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{ytd_run.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "ride": {
                        "count": ytd_ride.count,
                        "distance": {
                            "meters": ytd_ride.distance,
                            "formatted": f"{ytd_ride.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{ytd_ride.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": ytd_ride.moving_time,
                            "formatted": f"{ytd_ride.moving_time // 3600}h {(ytd_ride.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": ytd_ride.elevation_gain,
                            "formatted": f"{ytd_ride.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{ytd_ride.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "swim": {
                        "count": ytd_swim.count,
                        "distance": {
                            "meters": ytd_swim.distance,
                            "formatted": f"{ytd_swim.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{ytd_swim.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": ytd_swim.moving_time,
                            "formatted": f"{ytd_swim.moving_time // 3600}h {(ytd_swim.moving_time % 3600) // 60}m",
                        },
                    },
                }

            # All-time stats
            if stats_period == "all":
                all_run = stats.all_run_totals
                all_ride = stats.all_ride_totals
                all_swim = stats.all_swim_totals

                statistics["all_time"] = {
                    "description": "All time",
                    "run": {
                        "count": all_run.count,
                        "distance": {
                            "meters": all_run.distance,
                            "formatted": f"{all_run.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{all_run.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": all_run.moving_time,
                            "formatted": f"{all_run.moving_time // 3600}h {(all_run.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": all_run.elevation_gain,
                            "formatted": f"{all_run.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{all_run.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "ride": {
                        "count": all_ride.count,
                        "distance": {
                            "meters": all_ride.distance,
                            "formatted": f"{all_ride.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{all_ride.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": all_ride.moving_time,
                            "formatted": f"{all_ride.moving_time // 3600}h {(all_ride.moving_time % 3600) // 60}m",
                        },
                        "elevation_gain": {
                            "meters": all_ride.elevation_gain,
                            "formatted": f"{all_ride.elevation_gain:.0f} m"
                            if unit == "meters"
                            else f"{all_ride.elevation_gain * 3.28084:.0f} ft",
                        },
                    },
                    "swim": {
                        "count": all_swim.count,
                        "distance": {
                            "meters": all_swim.distance,
                            "formatted": f"{all_swim.distance / 1000:.1f} km"
                            if unit == "meters"
                            else f"{all_swim.distance * 0.000621371:.1f} mi",
                        },
                        "moving_time": {
                            "seconds": all_swim.moving_time,
                            "formatted": f"{all_swim.moving_time // 3600}h {(all_swim.moving_time % 3600) // 60}m",
                        },
                    },
                }

            data["statistics"] = statistics  # type: ignore[assignment]
            metadata["includes"].append(f"stats:{stats_period}")

        # Add zones if requested
        if include_zones:
            zones = await client.get_athlete_zones()

            zones_data = ResponseBuilder.format_zones(zones.model_dump())
            data["zones"] = zones_data  # type: ignore[assignment]
            metadata["includes"].append("zones")

        return ResponseBuilder.build_response(data, metadata=metadata)

    except StravaAPIError as e:
        error_type = "api_error"
        suggestions = []

        if e.status_code == 429:
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
