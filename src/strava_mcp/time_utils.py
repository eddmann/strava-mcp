"""Time range parsing utilities for activity queries.

This module provides utilities for parsing flexible time range strings
into concrete start/end datetime objects.
"""

import re
from datetime import datetime, timedelta
from typing import Literal

TimeRangePreset = Literal["recent", "7d", "30d", "90d", "ytd", "this-week", "this-month"]


def parse_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Parse time_range string into start/end dates.

    Supported formats:
    - "recent": Last 30 days
    - "7d", "30d", "90d": Last N days
    - "ytd": Year to date
    - "this-week": Current week (Monday to Sunday)
    - "this-month": Current month
    - "YYYY-MM-DD:YYYY-MM-DD": Custom date range

    Args:
        time_range: Time range string

    Returns:
        Tuple of (start_date, end_date) as datetime objects

    Raises:
        ValueError: If time_range format is invalid

    Examples:
        >>> start, end = parse_time_range("7d")
        >>> start, end = parse_time_range("2024-01-01:2024-01-31")
        >>> start, end = parse_time_range("ytd")
    """
    now = datetime.now()
    time_range = time_range.lower().strip()

    # Preset: recent (last 30 days)
    if time_range == "recent":
        start = now - timedelta(days=30)
        return start, now

    # Preset: Nd (last N days)
    if match := re.match(r"^(\d+)d$", time_range):
        days = int(match.group(1))
        if days <= 0:
            raise ValueError(f"Invalid days value: {days}. Must be positive.")
        if days > 365:
            raise ValueError(
                f"Invalid days value: {days}. Maximum is 365 days. "
                "Use custom date range for longer periods."
            )
        start = now - timedelta(days=days)
        return start, now

    # Preset: ytd (year to date)
    if time_range == "ytd":
        start = datetime(now.year, 1, 1)
        return start, now

    # Preset: this-week (Monday to Sunday)
    if time_range == "this-week":
        # Get Monday of current week
        days_since_monday = now.weekday()
        start = now - timedelta(days=days_since_monday)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now

    # Preset: this-month
    if time_range == "this-month":
        start = datetime(now.year, now.month, 1)
        return start, now

    # Custom range: YYYY-MM-DD:YYYY-MM-DD
    if ":" in time_range:
        try:
            start_str, end_str = time_range.split(":", 1)
            start = datetime.strptime(start_str.strip(), "%Y-%m-%d")
            end = datetime.strptime(end_str.strip(), "%Y-%m-%d")

            # Validate range
            if start > end:
                raise ValueError(
                    f"Invalid date range: start date ({start_str}) is after end date ({end_str})"
                )

            # Set end to end of day
            end = end.replace(hour=23, minute=59, second=59)

            return start, end
        except ValueError as e:
            if "Invalid date range:" in str(e):
                raise
            raise ValueError(
                f"Invalid date format in range '{time_range}'. "
                "Expected format: YYYY-MM-DD:YYYY-MM-DD"
            ) from e

    # Unknown format
    raise ValueError(
        f"Invalid time_range format: '{time_range}'. "
        "Supported formats: 'recent', '7d', '30d', '90d', 'ytd', 'this-week', "
        "'this-month', or 'YYYY-MM-DD:YYYY-MM-DD'"
    )


def format_date_range(start: datetime, end: datetime) -> str:
    """Format a date range into a human-readable string.

    Args:
        start: Start datetime
        end: End datetime

    Returns:
        Human-readable date range string

    Examples:
        >>> format_date_range(datetime(2024, 1, 1), datetime(2024, 1, 31))
        "2024-01-01 to 2024-01-31"
    """
    return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"


def get_range_description(time_range: str) -> str:
    """Get a human-readable description of a time range.

    Args:
        time_range: Time range string (same format as parse_time_range)

    Returns:
        Human-readable description

    Examples:
        >>> get_range_description("7d")
        "Last 7 days"
        >>> get_range_description("ytd")
        "Year to date"
    """
    time_range = time_range.lower().strip()

    if time_range == "recent":
        return "Last 30 days"

    if match := re.match(r"^(\d+)d$", time_range):
        days = int(match.group(1))
        return f"Last {days} days"

    if time_range == "ytd":
        return "Year to date"

    if time_range == "this-week":
        return "This week"

    if time_range == "this-month":
        return "This month"

    if ":" in time_range:
        try:
            start, end = parse_time_range(time_range)
            return format_date_range(start, end)
        except ValueError:
            return time_range

    return time_range
