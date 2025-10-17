"""Formatting utilities for Strava data."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 23m 45s"
    """
    if seconds < 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_distance(
    meters: float,
    unit: Literal["meters", "feet"] = "meters",
) -> str:
    """
    Format distance in meters to km or miles.

    Args:
        meters: Distance in meters
        unit: Measurement system preference

    Returns:
        Formatted string like "10.5 km" or "6.5 mi"
    """
    if unit == "feet":
        miles = meters / 1609.344
        return f"{miles:.2f} mi"
    else:
        km = meters / 1000
        return f"{km:.2f} km"


def format_elevation(
    meters: float,
    unit: Literal["meters", "feet"] = "meters",
) -> str:
    """
    Format elevation in meters to m or ft.

    Args:
        meters: Elevation in meters
        unit: Measurement system preference

    Returns:
        Formatted string like "150 m" or "492 ft"
    """
    if unit == "feet":
        feet = meters * 3.28084
        return f"{feet:.0f} ft"
    else:
        return f"{meters:.0f} m"


def format_speed(
    meters_per_second: float,
    unit: Literal["meters", "feet"] = "meters",
) -> str:
    """
    Format speed in m/s to km/h or mph.

    Args:
        meters_per_second: Speed in meters per second
        unit: Measurement system preference

    Returns:
        Formatted string like "25.5 km/h" or "15.8 mph"
    """
    if unit == "feet":
        mph = meters_per_second * 2.23694
        return f"{mph:.1f} mph"
    else:
        kmh = meters_per_second * 3.6
        return f"{kmh:.1f} km/h"


def format_pace(
    meters_per_second: float,
    unit: Literal["meters", "feet"] = "meters",
) -> str:
    """
    Format pace (inverse of speed) to min/km or min/mi.

    Args:
        meters_per_second: Speed in meters per second
        unit: Measurement system preference

    Returns:
        Formatted string like "4:30 /km" or "7:15 /mi"
    """
    if meters_per_second == 0:
        return "0:00 /km" if unit == "meters" else "0:00 /mi"

    if unit == "feet":
        # Pace in minutes per mile
        seconds_per_mile = 1609.344 / meters_per_second
        minutes = int(seconds_per_mile // 60)
        seconds = int(seconds_per_mile % 60)
        return f"{minutes}:{seconds:02d} /mi"
    else:
        # Pace in minutes per kilometer
        seconds_per_km = 1000 / meters_per_second
        minutes = int(seconds_per_km // 60)
        seconds = int(seconds_per_km % 60)
        return f"{minutes}:{seconds:02d} /km"


def format_datetime(dt: datetime) -> str:
    """
    Format datetime to readable string.

    Args:
        dt: Datetime object

    Returns:
        Formatted string like "2024-01-15 14:30:00"
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime) -> str:
    """
    Format datetime to date string.

    Args:
        dt: Datetime object

    Returns:
        Formatted string like "2024-01-15"
    """
    return dt.strftime("%Y-%m-%d")


def format_activity_type(activity_type: str, sport_type: str | None = None) -> str:
    """
    Format activity type with optional sport type.

    Args:
        activity_type: Activity type (e.g., "Ride", "Run")
        sport_type: More specific sport type (e.g., "MountainBikeRide")

    Returns:
        Formatted activity type
    """
    if sport_type and sport_type != activity_type:
        return f"{activity_type} ({sport_type})"
    return activity_type


def _calculate_avg(values: list[int] | list[float]) -> float:
    """Calculate average of numeric values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _calculate_normalized_power(watts: Sequence[int | float]) -> float:
    """
    Calculate Normalized Power (NP) from power data.

    Args:
        watts: List of power values in watts

    Returns:
        Normalized power value
    """
    if not watts or len(watts) < 30:
        return 0.0

    # 30-second rolling average
    rolling_avg: list[float] = []
    window = 30
    for i in range(len(watts) - window + 1):
        avg = sum(watts[i : i + window]) / window
        rolling_avg.append(avg**4)

    if not rolling_avg:
        return 0.0

    np_value = (sum(rolling_avg) / len(rolling_avg)) ** 0.25
    return round(np_value, 1)


def format_stream_stats(
    stream_name: str,
    values: list[int] | list[float],
    unit: Literal["meters", "feet"] = "meters",
) -> str:
    """
    Format statistics for a stream.

    Args:
        stream_name: Name of the stream (e.g., "heartrate", "watts")
        values: List of values
        unit: Measurement system preference

    Returns:
        Formatted statistics string
    """
    if not values:
        return f"{stream_name}: No data"

    stats: list[str] = []
    stats.append(f"Count: {len(values)}")
    stats.append(f"Max: {max(values)}")
    stats.append(f"Min: {min(values)}")
    stats.append(f"Avg: {_calculate_avg(values):.1f}")

    # Add specialized stats
    if stream_name == "watts" and isinstance(values[0], int):
        np = _calculate_normalized_power(values)
        stats.append(f"NP: {np}")
    elif stream_name == "velocity_smooth":
        max_kmh = max(values) * 3.6
        stats.append(f"Max: {max_kmh:.1f} km/h")

    return f"{stream_name}: {', '.join(stats)}"
