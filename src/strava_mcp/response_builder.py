"""Response builder utilities for structured JSON output.

This module provides utilities for building consistent, structured JSON responses
across all MCP tools. All tools return JSON with a standard structure:

{
    "data": {...},           # Main data payload
    "analysis": {...},       # Optional insights and computed metrics
    "metadata": {...}        # Query metadata, timestamps, includes
}
"""

import json
from datetime import datetime
from typing import Any, cast

from .formatters import (
    format_distance,
    format_duration,
    format_elevation,
    format_pace,
    format_speed,
)
from .models import MeasurementPreference


def _convert_datetimes(obj: Any) -> str | dict[str, Any] | list[Any] | Any:
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {str(k): _convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetimes(item) for item in obj]
    return obj


class ResponseBuilder:
    """Builder for standardized JSON responses."""

    @staticmethod
    def build_response(
        data: dict[str, Any],
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        query_type: str | None = None,
    ) -> str:
        """Build standardized JSON response.

        Args:
            data: Main data payload
            analysis: Optional analysis and insights
            metadata: Optional metadata (will be enriched with timestamp)
            query_type: Optional query type for metadata

        Returns:
            JSON string with structure:
            {
                "data": {...},
                "analysis": {...},
                "metadata": {
                    "fetched_at": "ISO timestamp",
                    "query_type": "...",
                    ...
                }
            }
        """
        # Convert datetime objects to ISO strings
        converted_data = cast(dict[str, Any], _convert_datetimes(data))
        converted_analysis: dict[str, Any] | None = None
        if analysis:
            converted_analysis = cast(dict[str, Any], _convert_datetimes(analysis))

        response: dict[str, Any] = {"data": converted_data}

        if converted_analysis:
            response["analysis"] = converted_analysis

        # Build metadata with timestamp
        meta = metadata or {}
        converted_meta = cast(dict[str, Any], _convert_datetimes(meta))
        converted_meta["fetched_at"] = datetime.now().isoformat()
        if query_type:
            converted_meta["query_type"] = query_type

        response["metadata"] = converted_meta

        return json.dumps(response, indent=2)

    @staticmethod
    def build_error_response(
        error_message: str,
        error_type: str = "error",
        suggestions: list[str] | None = None,
    ) -> str:
        """Build standardized error response.

        Args:
            error_message: Human-readable error message
            error_type: Type of error (e.g., "not_found", "rate_limit", "validation")
            suggestions: Optional list of suggestions to resolve the error

        Returns:
            JSON string with error structure
        """
        response: dict[str, dict[str, str | list[str]]] = {
            "error": {
                "message": error_message,
                "type": error_type,
                "timestamp": datetime.now().isoformat(),
            }
        }

        if suggestions:
            response["error"]["suggestions"] = suggestions

        return json.dumps(response, indent=2)

    @staticmethod
    def format_activity(
        activity: dict[str, Any], unit: MeasurementPreference = "meters"
    ) -> dict[str, Any]:
        """Format activity with both raw and formatted values.

        Args:
            activity: Activity data from Strava API
            unit: Unit preference for formatting

        Returns:
            Dict with nested structure containing raw and formatted values
        """
        formatted: dict[str, Any] = {
            "id": activity.get("id"),
            "name": activity.get("name"),
            "type": activity.get("type"),
            "sport_type": activity.get("sport_type"),
            "start_date": activity.get("start_date_local"),
        }

        # Distance
        if distance_m := activity.get("distance"):
            formatted["distance"] = {
                "meters": distance_m,
                "formatted": format_distance(distance_m, unit),
            }

        # Moving time
        if moving_time := activity.get("moving_time"):
            formatted["time"] = {
                "moving_seconds": moving_time,
                "formatted": format_duration(moving_time),
            }

        # Elapsed time (if different)
        if elapsed_time := activity.get("elapsed_time"):
            formatted["elapsed_time"] = {
                "seconds": elapsed_time,
                "formatted": format_duration(elapsed_time),
            }

        # Speed
        if avg_speed := activity.get("average_speed"):
            formatted["speed"] = {
                "avg_m_per_s": avg_speed,
                "avg_formatted": format_speed(avg_speed, unit),
            }

        if max_speed := activity.get("max_speed"):
            formatted["speed"] = formatted.get("speed", {})
            formatted["speed"]["max_m_per_s"] = max_speed
            formatted["speed"]["max_formatted"] = format_speed(max_speed, unit)

        # Pace (for running/walking)
        activity_type = activity.get("type", "").lower()
        if activity_type in ["run", "walk"] and moving_time and distance_m:
            meters_per_second = distance_m / moving_time
            avg_pace = format_pace(meters_per_second, unit)
            formatted["pace"] = {"avg_formatted": avg_pace}

        # Elevation
        if total_elevation := activity.get("total_elevation_gain"):
            formatted["elevation"] = {
                "gain_meters": total_elevation,
                "gain_formatted": format_elevation(total_elevation, unit),
            }

        # Heart rate
        if avg_hr := activity.get("average_heartrate"):
            formatted["heart_rate"] = {"avg_bpm": round(avg_hr)}

        if max_hr := activity.get("max_heartrate"):
            formatted["heart_rate"] = formatted.get("heart_rate", {})
            formatted["heart_rate"]["max_bpm"] = round(max_hr)

        # Power
        if avg_watts := activity.get("average_watts"):
            formatted["power"] = {"avg_watts": round(avg_watts)}

        if max_watts := activity.get("max_watts"):
            formatted["power"] = formatted.get("power", {})
            formatted["power"]["max_watts"] = round(max_watts)

        # Cadence
        if avg_cadence := activity.get("average_cadence"):
            formatted["cadence"] = {"avg_rpm": round(avg_cadence)}

        # Calories
        if calories := activity.get("calories"):
            formatted["calories"] = calories

        # Gear
        if gear_id := activity.get("gear_id"):
            formatted["gear_id"] = gear_id

        # Trainer/commute flags
        if "trainer" in activity:
            formatted["trainer"] = activity["trainer"]
        if "commute" in activity:
            formatted["commute"] = activity["commute"]

        return formatted

    @staticmethod
    def format_lap(
        lap: dict[str, Any], lap_number: int, unit: MeasurementPreference = "meters"
    ) -> dict[str, Any]:
        """Format lap with both raw and formatted values.

        Args:
            lap: Lap data from Strava API
            lap_number: Lap number (1-indexed)
            unit: Unit preference for formatting

        Returns:
            Dict with nested structure containing raw and formatted values
        """
        formatted: dict[str, Any] = {
            "lap_number": lap_number,
            "name": lap.get("name", f"Lap {lap_number}"),
        }

        # Distance
        if distance_m := lap.get("distance"):
            formatted["distance"] = {
                "meters": distance_m,
                "formatted": format_distance(distance_m, unit),
            }

        # Time
        if moving_time := lap.get("moving_time"):
            formatted["time"] = {
                "moving_seconds": moving_time,
                "formatted": format_duration(moving_time),
            }

        if elapsed_time := lap.get("elapsed_time"):
            formatted["elapsed_time"] = {
                "seconds": elapsed_time,
                "formatted": format_duration(elapsed_time),
            }

        # Speed
        if avg_speed := lap.get("average_speed"):
            formatted["speed"] = {
                "avg_m_per_s": avg_speed,
                "avg_formatted": format_speed(avg_speed, unit),
            }

        if max_speed := lap.get("max_speed"):
            formatted["speed"] = formatted.get("speed", {})
            formatted["speed"]["max_m_per_s"] = max_speed
            formatted["speed"]["max_formatted"] = format_speed(max_speed, unit)

        # Pace
        if moving_time and distance_m:
            meters_per_second = distance_m / moving_time
            avg_pace = format_pace(meters_per_second, unit)
            formatted["pace"] = {"avg_formatted": avg_pace}

        # Elevation
        if total_elevation := lap.get("total_elevation_gain"):
            formatted["elevation"] = {
                "gain_meters": total_elevation,
                "gain_formatted": format_elevation(total_elevation, unit),
            }

        # Heart rate
        if avg_hr := lap.get("average_heartrate"):
            formatted["heart_rate"] = {"avg_bpm": round(avg_hr)}

        if max_hr := lap.get("max_heartrate"):
            formatted["heart_rate"] = formatted.get("heart_rate", {})
            formatted["heart_rate"]["max_bpm"] = round(max_hr)

        # Power
        if avg_watts := lap.get("average_watts"):
            formatted["power"] = {"avg_watts": round(avg_watts)}

        if max_watts := lap.get("max_watts"):
            formatted["power"] = formatted.get("power", {})
            formatted["power"]["max_watts"] = round(max_watts)

        # Cadence
        if avg_cadence := lap.get("average_cadence"):
            formatted["cadence"] = {"avg_rpm": round(avg_cadence)}

        return formatted

    @staticmethod
    def format_zones(zones: dict[str, Any]) -> dict[str, Any]:
        """Format training zones with both raw and formatted values.

        Args:
            zones: Zones data from Strava API

        Returns:
            Dict with formatted zone data
        """
        formatted: dict[str, Any] = {}

        # Heart rate zones
        if hr_zones := zones.get("heart_rate"):
            zone_list: list[dict[str, Any]] = []
            for zone in hr_zones.get("zones", []):
                zone_list.append(
                    {"min": zone.get("min"), "max": zone.get("max")}
                )
            formatted["heart_rate"] = {
                "custom_zones": hr_zones.get("custom_zones", False),
                "zones": zone_list,
            }

        # Power zones
        if power_zones := zones.get("power"):
            power_zone_list: list[dict[str, Any]] = []
            for zone in power_zones.get("zones", []):
                power_zone_list.append(
                    {"min": zone.get("min"), "max": zone.get("max")})
            formatted["power"] = {
                "zones": power_zone_list,
            }

        return formatted

    @staticmethod
    def aggregate_activities(
        activities: list[dict[str, Any]], unit: MeasurementPreference = "meters"
    ) -> dict[str, Any]:
        """Aggregate metrics across multiple activities.

        Args:
            activities: List of activity data
            unit: Unit preference for formatting

        Returns:
            Dict with aggregated metrics
        """
        if not activities:
            return {}

        total_distance = sum(a.get("distance", 0) for a in activities)
        total_time = sum(a.get("moving_time", 0) for a in activities)
        total_elevation = sum(a.get("total_elevation_gain", 0)
                              for a in activities)

        aggregated: dict[str, Any] = {
            "count": len(activities),
            "total_distance": {
                "meters": total_distance,
                "formatted": format_distance(total_distance, unit),
            },
            "total_time": {
                "seconds": total_time,
                "formatted": format_duration(total_time),
            },
            "total_elevation": {
                "meters": total_elevation,
                "formatted": format_elevation(total_elevation, unit),
            },
        }

        # Average distance per activity
        if len(activities) > 0:
            avg_distance = total_distance / len(activities)
            aggregated["avg_distance_per_activity"] = {
                "meters": avg_distance,
                "formatted": format_distance(avg_distance, unit),
            }

        # Average pace (if applicable)
        if total_time > 0 and total_distance > 0:
            avg_speed = total_distance / total_time
            aggregated["avg_speed"] = {
                "m_per_s": avg_speed,
                "formatted": format_speed(avg_speed, unit),
            }

        return aggregated
