"""Tests for formatting utilities."""

from strava_mcp.formatters import (
    format_distance,
    format_duration,
    format_elevation,
    format_pace,
    format_speed,
)


class TestFormatters:
    """Test formatting functions."""

    def test_format_distance_meters(self):
        """Test distance formatting in meters."""
        assert format_distance(1000, "meters") == "1.00 km"
        assert format_distance(500, "meters") == "0.50 km"
        assert format_distance(1500, "meters") == "1.50 km"

    def test_format_distance_feet(self):
        """Test distance formatting in feet."""
        assert format_distance(1609.34, "feet") == "1.00 mi"
        assert format_distance(804.67, "feet") == "0.50 mi"

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(60) == "1m"
        assert format_duration(3600) == "1h"

    def test_format_speed(self):
        """Test speed formatting."""
        # 10 m/s = 36 km/h
        assert format_speed(10.0) == "36.0 km/h"
        assert format_speed(5.0) == "18.0 km/h"

    def test_format_pace(self):
        """Test pace formatting."""
        # 3.33 m/s ≈ 5:00 min/km
        result = format_pace(3.33)
        assert "5:0" in result  # Allow for rounding variations

    def test_format_elevation(self):
        """Test elevation formatting."""
        assert format_elevation(100, "meters") == "100 m"
        # 100 meters * 3.28084 = 328 ft
        assert format_elevation(100, "feet") == "328 ft"
