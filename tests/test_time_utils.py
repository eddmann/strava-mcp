"""Tests for time_utils module."""

from datetime import datetime

import pytest

from strava_mcp.time_utils import format_date_range, get_range_description, parse_time_range


class TestParseTimeRange:
    """Test parse_time_range function."""

    def test_parse_recent(self):
        """Test parsing 'recent' preset."""
        start, end = parse_time_range("recent")
        assert (end - start).days == 30

    def test_parse_days(self):
        """Test parsing '7d', '30d', '90d' formats."""
        start, end = parse_time_range("7d")
        assert (end - start).days == 7

        start, end = parse_time_range("30d")
        assert (end - start).days == 30

        start, end = parse_time_range("90d")
        assert (end - start).days == 90

    def test_parse_ytd(self):
        """Test parsing 'ytd' (year to date)."""
        start, end = parse_time_range("ytd")
        now = datetime.now()
        assert start.year == now.year
        assert start.month == 1
        assert start.day == 1

    def test_parse_this_week(self):
        """Test parsing 'this-week'."""
        start, end = parse_time_range("this-week")
        # Should start on Monday
        assert start.weekday() == 0

    def test_parse_this_month(self):
        """Test parsing 'this-month'."""
        start, end = parse_time_range("this-month")
        now = datetime.now()
        assert start.year == now.year
        assert start.month == now.month
        assert start.day == 1

    def test_parse_custom_range(self):
        """Test parsing custom date range."""
        start, end = parse_time_range("2024-01-01:2024-01-31")
        assert start.year == 2024
        assert start.month == 1
        assert start.day == 1
        assert end.year == 2024
        assert end.month == 1
        assert end.day == 31

    def test_parse_invalid_days(self):
        """Test parsing invalid days value."""
        with pytest.raises(ValueError, match="Must be positive"):
            parse_time_range("0d")

        with pytest.raises(ValueError, match="Maximum is 365 days"):
            parse_time_range("500d")

    def test_parse_invalid_custom_range(self):
        """Test parsing invalid custom range."""
        with pytest.raises(ValueError, match="start date.*is after end date"):
            parse_time_range("2024-12-31:2024-01-01")

        with pytest.raises(ValueError, match="Invalid date format"):
            parse_time_range("2024-13-01:2024-12-31")

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        with pytest.raises(ValueError, match="Invalid time_range format"):
            parse_time_range("invalid")


class TestGetRangeDescription:
    """Test get_range_description function."""

    def test_describe_recent(self):
        """Test describing 'recent'."""
        assert get_range_description("recent") == "Last 30 days"

    def test_describe_days(self):
        """Test describing day formats."""
        assert get_range_description("7d") == "Last 7 days"
        assert get_range_description("30d") == "Last 30 days"

    def test_describe_ytd(self):
        """Test describing 'ytd'."""
        assert get_range_description("ytd") == "Year to date"

    def test_describe_this_week(self):
        """Test describing 'this-week'."""
        assert get_range_description("this-week") == "This week"

    def test_describe_this_month(self):
        """Test describing 'this-month'."""
        assert get_range_description("this-month") == "This month"

    def test_describe_custom_range(self):
        """Test describing custom range."""
        result = get_range_description("2024-01-01:2024-01-31")
        assert "2024-01-01" in result
        assert "2024-01-31" in result


class TestFormatDateRange:
    """Test format_date_range function."""

    def test_format_date_range(self):
        """Test formatting date range."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = format_date_range(start, end)
        assert result == "2024-01-01 to 2024-01-31"
