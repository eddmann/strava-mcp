"""Tests for pagination utilities."""

import pytest

from strava_mcp.pagination import (
    build_pagination_info,
    decode_cursor,
    encode_cursor,
)


class TestCursorEncoding:
    """Test cursor encoding and decoding."""

    def test_encode_cursor_simple(self):
        """Test encoding a simple cursor with just page number."""
        cursor = encode_cursor(2)
        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_encode_cursor_with_filters(self):
        """Test encoding cursor with filters."""
        filters = {"time_range": "30d", "activity_type": "Run"}
        cursor = encode_cursor(3, filters)
        assert isinstance(cursor, str)

    def test_decode_cursor_simple(self):
        """Test decoding a simple cursor."""
        cursor = encode_cursor(5)
        decoded = decode_cursor(cursor)
        assert decoded.get("page") == 5

    def test_decode_cursor_with_filters(self):
        """Test decoding cursor with filters."""
        filters = {"time_range": "7d", "activity_type": "Ride"}
        cursor = encode_cursor(2, filters)
        decoded = decode_cursor(cursor)

        assert decoded.get("page") == 2
        cursor_filters = decoded.get("filters", {})
        assert cursor_filters.get("time_range") == "7d"
        assert cursor_filters.get("activity_type") == "Ride"

    def test_decode_invalid_cursor(self):
        """Test decoding invalid cursor raises ValueError."""
        with pytest.raises(ValueError, match="Invalid pagination cursor"):
            decode_cursor("invalid_cursor")

    def test_round_trip_encoding(self):
        """Test encoding and decoding round trip."""
        original_page = 42
        original_filters = {
            "bounds": "37.77,-122.45,37.80,-122.40",
            "activity_type": "riding",
        }

        cursor = encode_cursor(original_page, original_filters)
        decoded = decode_cursor(cursor)

        assert decoded.get("page") == original_page
        assert decoded.get("filters") == original_filters


class TestPaginationInfo:
    """Test pagination info building."""

    def test_build_pagination_info_no_more_pages(self):
        """Test building pagination info when no more pages."""
        info = build_pagination_info(
            returned_count=5,
            limit=10,
            current_page=1,
            has_more=False,
        )

        assert info["returned"] == 5
        assert info["limit"] == 10
        assert info["has_more"] is False
        assert info["cursor"] is None

    def test_build_pagination_info_has_more(self):
        """Test building pagination info when more pages exist."""
        info = build_pagination_info(
            returned_count=10,
            limit=10,
            current_page=1,
            has_more=True,
        )

        assert info["returned"] == 10
        assert info["limit"] == 10
        assert info["has_more"] is True
        assert info["cursor"] is not None

        # Verify cursor encodes next page
        cursor = info["cursor"]
        assert cursor is not None
        decoded = decode_cursor(cursor)
        assert decoded.get("page") == 2

    def test_build_pagination_info_with_filters(self):
        """Test building pagination info with filters in cursor."""
        filters = {"time_range": "30d"}
        info = build_pagination_info(
            returned_count=10,
            limit=10,
            current_page=2,
            has_more=True,
            filters=filters,
        )

        assert info["cursor"] is not None
        cursor = info["cursor"]
        assert cursor is not None
        decoded = decode_cursor(cursor)
        assert decoded.get("page") == 3
        cursor_filters = decoded.get("filters", {})
        assert cursor_filters.get("time_range") == "30d"

    def test_build_pagination_info_preserves_filters_across_pages(self):
        """Test that filters are preserved when paginating."""
        filters = {"activity_type": "Run", "time_range": "7d"}

        # Page 1
        info1 = build_pagination_info(
            returned_count=10,
            limit=10,
            current_page=1,
            has_more=True,
            filters=filters,
        )

        cursor1 = info1["cursor"]
        assert cursor1 is not None
        decoded1 = decode_cursor(cursor1)
        assert decoded1.get("filters") == filters

        # Page 2 (using filters from decoded cursor)
        info2 = build_pagination_info(
            returned_count=10,
            limit=10,
            current_page=2,
            has_more=True,
            filters=decoded1.get("filters"),
        )

        cursor2 = info2["cursor"]
        assert cursor2 is not None
        decoded2 = decode_cursor(cursor2)
        assert decoded2.get("filters") == filters
