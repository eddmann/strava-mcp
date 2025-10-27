"""Activity filtering utilities for client-side filtering.

This module provides client-side filtering capabilities for activities,
supporting distance ranges, title search, and race detection.
"""

import re

from .models import SummaryActivity

# Race distance ranges with ±10% tolerance (in meters)
RACE_DISTANCE_RANGES: dict[str, tuple[int, int | None]] = {
    "5k": (4500, 5500),
    "10k": (9000, 11000),
    "15k": (13500, 16500),
    "half-marathon": (20000, 22000),
    "half marathon": (20000, 22000),  # Alternative spelling
    "half": (20000, 22000),  # Short form
    "marathon": (41000, 43000),
    "ultra": (43000, None),  # Anything beyond marathon
    "50k": (45000, 55000),
    "100k": (90000, 110000),
}

# Race workout type mapping
# Run races: workout_type = 1
# Ride races: workout_type = 11
RACE_WORKOUT_TYPES: dict[str, int] = {
    "Run": 1,
    "Ride": 11,
}

# Distance unit conversion factors to meters
DISTANCE_UNITS: dict[str, float] = {
    "km": 1000.0,
    "kilometers": 1000.0,
    "kilometer": 1000.0,
    "mi": 1609.34,
    "miles": 1609.34,
    "mile": 1609.34,
    "m": 1.0,
    "meters": 1.0,
    "meter": 1.0,
}


def parse_distance_with_unit(value: str) -> int:
    """Parse distance string with optional unit suffix to meters.

    Supports numeric values with optional unit suffixes (km, mi, m).
    Units are case-insensitive. If no unit is provided, defaults to meters.

    Examples:
        "10km" → 10000
        "5mi" → 8047
        "42195m" → 42195
        "10000" → 10000 (defaults to meters)
        "5.5km" → 5500
        "3.1 mi" → 4990 (space before unit supported)

    Args:
        value: Distance string with optional unit (e.g., "10km", "5mi", "10000")

    Returns:
        Distance in meters (rounded to nearest integer)

    Raises:
        ValueError: If format is invalid or unit is not recognized
    """
    value_stripped = value.strip()

    # Regex pattern: optional minus sign, number (int or decimal), optional whitespace, optional unit
    # Pattern: (optional -)(decimal number) (optional whitespace) (optional unit letters)
    pattern = r"^(-?[\d.]+)\s*([a-zA-Z]*)$"
    match = re.match(pattern, value_stripped)

    if not match:
        raise ValueError(
            f"Invalid distance format: '{value}'. Expected numeric value with optional unit "
            "(e.g., '10km', '5mi', '10000')"
        )

    distance_str, unit = match.groups()

    # Parse the numeric value
    try:
        distance_value = float(distance_str)
    except ValueError as e:
        raise ValueError(f"Invalid numeric value: '{distance_str}'") from e

    if distance_value < 0:
        raise ValueError(f"Distance cannot be negative: {distance_value}")

    # If no unit specified, default to meters
    if not unit:
        return round(distance_value)

    # Convert unit to lowercase for lookup
    unit_lower = unit.lower()

    # Check if unit is recognized
    if unit_lower not in DISTANCE_UNITS:
        valid_units = list(set(DISTANCE_UNITS.keys()))
        raise ValueError(
            f"Unknown unit: '{unit}'. Supported units: {', '.join(sorted(valid_units))}"
        )

    # Convert to meters
    conversion_factor = DISTANCE_UNITS[unit_lower]
    meters = distance_value * conversion_factor

    return round(meters)


def parse_distance(value: str) -> tuple[int | None, int | None]:
    """Parse distance string to (min, max) in meters.

    Supports multiple input formats with optional unit suffixes (km, mi, m).
    Units are case-insensitive. If no unit provided, defaults to meters.

    Formats:
    1. Race distance names (with ±10% tolerance):
       "5k" → (4500, 5500)
       "marathon" → (41000, 43000)
       "ultra" → (43000, None)

    2. Numeric value with unit and buffer (±10%):
       "10km" → (9000, 11000)
       "5mi" → (7239, 8851)
       "10000" → (9000, 11000) - defaults to meters

    3. Exact range with units (no buffer):
       "5km:10km" → (5000, 10000)
       "3mi:6mi" → (4828, 9656)
       "10000:15000" → (10000, 15000) - defaults to meters
       ":10km" → (None, 10000) - open-ended minimum
       "5mi:" → (8047, None) - open-ended maximum

    Args:
        value: Distance filter string

    Returns:
        Tuple of (min_distance, max_distance) in meters
        Either value can be None for open-ended ranges

    Raises:
        ValueError: If distance format is invalid or units are mixed in range
    """
    value_lower = value.lower().strip()

    # Check if it's a race distance name (must check before unit parsing)
    if value_lower in RACE_DISTANCE_RANGES:
        return RACE_DISTANCE_RANGES[value_lower]

    # Check if it's a range (format: "min:max")
    if ":" in value:
        try:
            parts = value.split(":")
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid range format: '{value}'. Use 'min:max' (e.g., '10km:15km', '10000:15000')"
                )

            min_str, max_str = parts

            # Parse min and max distances (with unit support)
            min_distance = parse_distance_with_unit(min_str.strip()) if min_str.strip() else None
            max_distance = parse_distance_with_unit(max_str.strip()) if max_str.strip() else None

            # Validate range
            if (
                min_distance is not None
                and max_distance is not None
                and min_distance > max_distance
            ):
                raise ValueError(
                    f"Minimum distance ({min_distance}m) cannot be greater than maximum ({max_distance}m)"
                )

            return (min_distance, max_distance)
        except ValueError as e:
            # Re-raise if it's already a formatted error message
            if any(
                phrase in str(e)
                for phrase in ["cannot be greater", "Invalid distance format", "Unknown unit"]
            ):
                raise
            # Re-package parsing errors
            raise ValueError(f"Invalid range format: '{value}'. {str(e)}") from e

    # Numeric value with optional unit and ±10% buffer
    try:
        distance = parse_distance_with_unit(value)

        # Apply ±10% buffer
        buffer = int(distance * 0.1)
        return (distance - buffer, distance + buffer)
    except ValueError as e:
        # Re-raise if it's already a formatted error message
        if any(
            phrase in str(e)
            for phrase in ["cannot be negative", "Invalid distance format", "Unknown unit"]
        ):
            raise
        # Provide helpful error message with examples for other errors
        raise ValueError(
            f"Invalid distance format: '{value}'. Supported formats:\n"
            "  - Race names: '5k', '10k', 'half-marathon', 'marathon', 'ultra'\n"
            "  - Numeric with unit and ±10% buffer: '10km', '5mi', '10000' (defaults to meters)\n"
            "  - Exact range with units: '5km:10km', '3mi:6mi', '10000:15000'"
        ) from e


def filter_by_distance(
    activities: list[SummaryActivity],
    min_distance: int | None = None,
    max_distance: int | None = None,
) -> list[SummaryActivity]:
    """Filter activities by distance range.

    Args:
        activities: List of activities to filter
        min_distance: Minimum distance in meters (inclusive)
        max_distance: Maximum distance in meters (inclusive)

    Returns:
        Filtered list of activities
    """
    if min_distance is None and max_distance is None:
        return activities

    filtered: list[SummaryActivity] = []
    for activity in activities:
        distance = activity.distance

        if min_distance is not None and distance < min_distance:
            continue
        if max_distance is not None and distance > max_distance:
            continue

        filtered.append(activity)

    return filtered


def filter_by_title(
    activities: list[SummaryActivity],
    search: str,
    case_sensitive: bool = False,
) -> list[SummaryActivity]:
    """Filter activities by title substring.

    Args:
        activities: List of activities to filter
        search: Substring to search for in activity names
        case_sensitive: Whether to perform case-sensitive search (default: False)

    Returns:
        Filtered list of activities
    """
    if case_sensitive:
        return [activity for activity in activities if search in activity.name]
    else:
        search_lower = search.lower()
        return [activity for activity in activities if search_lower in activity.name.lower()]


def filter_by_race(
    activities: list[SummaryActivity],
    is_race: bool,
) -> list[SummaryActivity]:
    """Filter activities by race status.

    Race detection logic:
    - Run races: workout_type == 1
    - Ride races: workout_type == 11
    - Other activity types: Not considered races

    Args:
        activities: List of activities to filter
        is_race: True to get only races, False to get only non-races

    Returns:
        Filtered list of activities
    """
    filtered: list[SummaryActivity] = []
    for activity in activities:
        # Check if this activity type has race detection
        expected_race_workout = RACE_WORKOUT_TYPES.get(activity.type)

        if expected_race_workout is None:
            # Activity type doesn't have race detection (e.g., Swim, Walk)
            # Only include in non-race filter
            if not is_race:
                filtered.append(activity)
            continue

        # Check if workout_type matches the race type
        is_activity_race = activity.workout_type == expected_race_workout

        if is_race == is_activity_race:
            filtered.append(activity)

    return filtered


def apply_filters(
    activities: list[SummaryActivity],
    activity_type: str | None = None,
    distance_min: int | None = None,
    distance_max: int | None = None,
    title_contains: str | None = None,
    is_race: bool | None = None,
) -> list[SummaryActivity]:
    """Apply all filters with AND logic.

    All filters are applied sequentially, and an activity must match
    all specified criteria to be included in the result.

    Args:
        activities: List of activities to filter
        activity_type: Filter by activity type (e.g., "Run", "Ride")
        distance_min: Minimum distance in meters
        distance_max: Maximum distance in meters
        title_contains: Substring to search for in activity names
        is_race: Filter by race status (True=races only, False=non-races only)

    Returns:
        Filtered list of activities
    """
    filtered = activities

    # Filter by activity type
    if activity_type:
        filtered = [a for a in filtered if a.type == activity_type]

    # Filter by distance
    if distance_min is not None or distance_max is not None:
        filtered = filter_by_distance(filtered, distance_min, distance_max)

    # Filter by title
    if title_contains:
        filtered = filter_by_title(filtered, title_contains)

    # Filter by race status
    if is_race is not None:
        filtered = filter_by_race(filtered, is_race)

    return filtered
