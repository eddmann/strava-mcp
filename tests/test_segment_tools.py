"""Comprehensive tests for segment tools."""

import json

import pytest
from fastmcp import Client

from strava_mcp.server import mcp
from tests.fixtures.segment_fixtures import (
    DETAILED_SEGMENT,
    EXPLORE_SEGMENTS_RESPONSE,
    SEGMENT_EFFORTS_LIST,
    SEGMENT_LEADERBOARD,
    SUMMARY_SEGMENT,
)
from tests.helpers import get_text_content
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestQuerySegments:
    """Test query_segments tool."""

    async def test_query_segments_single_segment(self, stub_api):
        """Test querying single segment by ID."""
        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"segment_id": segment_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert "segment" in data["data"]
        assert data["data"]["segment"]["id"] == segment_id
        assert data["data"]["segment"]["name"] == "Hawk Hill"

        # Check structured metrics
        assert "meters" in data["data"]["segment"]["distance"]
        assert "formatted" in data["data"]["segment"]["distance"]
        assert "percent" in data["data"]["segment"]["average_grade"]
        assert "formatted" in data["data"]["segment"]["average_grade"]

        # Check metadata
        assert data["metadata"]["query_type"] == "single_segment"
        assert data["metadata"]["segment_id"] == segment_id

    async def test_query_segments_with_efforts(self, stub_api):
        """Test querying segment with efforts history."""
        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)
        stub_api.stub_segment_efforts_endpoint(segment_id, SEGMENT_EFFORTS_LIST)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments", {"segment_id": segment_id, "include_efforts": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "segment" in data["data"]
        assert "efforts" in data["data"]
        assert len(data["data"]["efforts"]) > 0

        # Check effort structure
        effort = data["data"]["efforts"][0]
        assert "id" in effort
        assert "elapsed_time" in effort
        assert "seconds" in effort["elapsed_time"]
        assert "formatted" in effort["elapsed_time"]

        # Check metadata
        assert "includes" in data["metadata"]
        assert "efforts" in data["metadata"]["includes"]

    async def test_query_segments_starred_list(self, stub_api):
        """Test querying starred segments."""
        segments = [SUMMARY_SEGMENT, {**SUMMARY_SEGMENT, "id": 2, "name": "Segment 2"}]
        stub_api.stub_starred_segments_endpoint(segments)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"starred_only": True})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "segments" in data["data"]
        assert "count" in data["data"]
        assert data["data"]["count"] == 2
        assert len(data["data"]["segments"]) == 2

        # Check segment structure
        segment = data["data"]["segments"][0]
        assert "id" in segment
        assert "name" in segment
        assert "distance" in segment
        assert "meters" in segment["distance"]
        assert "formatted" in segment["distance"]

        # Check metadata
        assert data["metadata"]["query_type"] == "starred_segments"

    async def test_query_segments_starred_empty(self, stub_api):
        """Test querying starred segments with no results."""
        stub_api.stub_starred_segments_endpoint([])

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"starred_only": True})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["count"] == 0
        assert data["data"]["segments"] == []

    async def test_query_segments_explore(self, stub_api):
        """Test exploring segments in geographic area."""
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"bounds": bounds})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "segments" in data["data"]
        assert "count" in data["data"]
        assert data["data"]["count"] == 2

        # Check segment structure
        segment = data["data"]["segments"][0]
        assert "id" in segment
        assert "name" in segment
        assert "climb_category" in segment
        assert "climb_category_desc" in segment
        assert "avg_grade" in segment
        assert "starred" in segment

        # Check metadata
        assert data["metadata"]["query_type"] == "explore_segments"
        assert data["metadata"]["bounds"] == bounds

    async def test_query_segments_explore_with_activity_type(self, stub_api):
        """Test exploring segments with activity type filter."""
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments", {"bounds": bounds, "activity_type": "riding"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["count"] > 0
        assert data["metadata"]["activity_type"] == "riding"

    async def test_query_segments_explore_with_climb_categories(self, stub_api):
        """Test exploring segments with climb category filters."""
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments",
                {"bounds": bounds, "activity_type": "riding", "min_category": 1, "max_category": 3},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["count"] > 0
        assert data["metadata"]["min_category"] == 1
        assert data["metadata"]["max_category"] == 3

    async def test_query_segments_explore_invalid_bounds(self):
        """Test exploring segments with invalid bounds format."""
        bounds = "37.7,-122.5"  # Only 2 values instead of 4
        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"bounds": bounds})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]

    async def test_query_segments_default_starred(self, stub_api):
        """Test that default query returns starred segments."""
        segments = [SUMMARY_SEGMENT]
        stub_api.stub_starred_segments_endpoint(segments)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["query_type"] == "starred_segments"

    async def test_query_segments_with_limit(self, stub_api):
        """Test querying segments with custom limit."""
        segments = [SUMMARY_SEGMENT for _ in range(50)]
        stub_api.stub_starred_segments_endpoint(segments)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"starred_only": True, "limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should return max 10 segments
        assert len(data["data"]["segments"]) <= 10

    async def test_query_segments_with_feet_units(self, stub_api):
        """Test querying segments with feet/miles units."""
        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments", {"segment_id": segment_id, "unit": "feet"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check that formatted values use miles/feet
        assert "mi" in data["data"]["segment"]["distance"]["formatted"]
        assert "ft" in data["data"]["segment"]["elevation_high"]["formatted"]

    async def test_query_segments_not_found(self, stub_api):
        """Test querying non-existent segment."""
        stub_api.stub_error_response("/segments/999999", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"segment_id": 999999})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]


class TestStarSegment:
    """Test star_segment tool."""

    async def test_star_segment_success(self, stub_api):
        """Test successful segment starring."""
        segment_id = 229781
        starred_segment = {**DETAILED_SEGMENT, "starred": True}
        stub_api.stub_star_segment_endpoint(segment_id, starred_segment)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "star_segment", {"segment_id": segment_id, "starred": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert data["data"]["segment_id"] == segment_id
        assert data["data"]["starred"] is True
        assert data["data"]["success"] is True

        # Check metadata
        assert "metadata" in data

    async def test_unstar_segment_success(self, stub_api):
        """Test successful segment unstarring."""
        segment_id = 229781
        unstarred_segment = {**DETAILED_SEGMENT, "starred": False}
        stub_api.stub_star_segment_endpoint(segment_id, unstarred_segment)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "star_segment", {"segment_id": segment_id, "starred": False}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["segment_id"] == segment_id
        assert data["data"]["starred"] is False
        assert data["data"]["success"] is True

    async def test_star_segment_not_found(self, stub_api):
        """Test starring non-existent segment."""
        stub_api.stub_error_response("/segments/999999/starred", method="PUT", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("star_segment", {"segment_id": 999999, "starred": True})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]

    async def test_star_segment_rate_limit(self, stub_api):
        """Test starring segment with rate limit error."""
        stub_api.stub_error_response("/segments/229781/starred", method="PUT", status_code=429)

        async with Client(mcp) as client:
            result = await client.call_tool("star_segment", {"segment_id": 229781, "starred": True})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]


class TestGetSegmentLeaderboard:
    """Test get_segment_leaderboard tool."""

    async def test_get_segment_leaderboard_success(self, stub_api):
        """Test successful segment leaderboard retrieval."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD)

        async with Client(mcp) as client:
            result = await client.call_tool("get_segment_leaderboard", {"segment_id": segment_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert "entries" in data["data"]
        assert "entry_count" in data["data"]
        assert data["data"]["entry_count"] == 5

        # Check entry structure
        entry = data["data"]["entries"][0]
        assert "rank" in entry
        assert "athlete_name" in entry
        assert "elapsed_time" in entry
        assert "seconds" in entry["elapsed_time"]
        assert "formatted" in entry["elapsed_time"]

        # Check metadata
        assert data["metadata"]["segment_id"] == segment_id
        assert "filters" in data["metadata"]

    async def test_get_segment_leaderboard_with_gender_filter(self, stub_api):
        """Test segment leaderboard with gender filter."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, gender="M")

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "gender": "M"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["gender"] == "M"

    async def test_get_segment_leaderboard_with_age_group(self, stub_api):
        """Test segment leaderboard with age group filter."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, age_group="25_34"
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "age_group": "25_34"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["age_group"] == "25_34"

    async def test_get_segment_leaderboard_with_weight_class(self, stub_api):
        """Test segment leaderboard with weight class filter."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, weight_class="75_84"
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "weight_class": "75_84"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["weight_class"] == "75_84"

    async def test_get_segment_leaderboard_with_following(self, stub_api):
        """Test segment leaderboard with following filter."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, following=True)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "following": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["following"] is True

    async def test_get_segment_leaderboard_with_club(self, stub_api):
        """Test segment leaderboard with club filter."""
        segment_id = 229781
        club_id = 12345
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, club_id=club_id)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "club_id": club_id}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["club_id"] == club_id

    async def test_get_segment_leaderboard_with_date_range(self, stub_api):
        """Test segment leaderboard with date range filter."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, date_range="this_year"
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "date_range": "this_year"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["filters"]["date_range"] == "this_year"

    async def test_get_segment_leaderboard_with_multiple_filters(self, stub_api):
        """Test segment leaderboard with multiple filters."""
        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id,
            SEGMENT_LEADERBOARD,
            gender="F",
            age_group="35_44",
            date_range="this_month",
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard",
                {
                    "segment_id": segment_id,
                    "gender": "F",
                    "age_group": "35_44",
                    "date_range": "this_month",
                },
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        filters = data["metadata"]["filters"]
        assert filters["gender"] == "F"
        assert filters["age_group"] == "35_44"
        assert filters["date_range"] == "this_month"

    async def test_get_segment_leaderboard_empty(self, stub_api):
        """Test segment leaderboard with no entries."""
        segment_id = 229781
        empty_leaderboard = {
            "entry_count": 0,
            "effort_count": 0,
            "kom_type": "kom",
            "entries": [],
        }
        stub_api.stub_segment_leaderboard_endpoint(segment_id, empty_leaderboard)

        async with Client(mcp) as client:
            result = await client.call_tool("get_segment_leaderboard", {"segment_id": segment_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["entry_count"] == 0
        assert data["data"]["entries"] == []

    async def test_get_segment_leaderboard_not_found(self, stub_api):
        """Test segment leaderboard with non-existent segment."""
        stub_api.stub_error_response("/segments/999999/leaderboard", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("get_segment_leaderboard", {"segment_id": 999999})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]


class TestSegmentPagination:
    """Test pagination behavior for segment tools."""

    async def test_query_segments_pagination_starred(self, respx_mock):
        """Test pagination for starred segments list."""
        from httpx import Response

        # Create 11 segments (limit+1 to trigger has_more)
        segments = [{**SUMMARY_SEGMENT, "id": 5000 + i, "name": f"Segment {i}"} for i in range(11)]

        def segments_response(request):
            return Response(200, json=segments)

        respx_mock.get("/segments/starred").mock(side_effect=segments_response)

        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"starred_only": True, "limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "pagination" in data
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert len(data["data"]["segments"]) == 10

    async def test_query_segments_explore_pagination(self, stub_api):
        """Test client-side pagination for explore segments."""
        # Create 25 segments in explore result
        all_segments = [
            {
                "id": 6000 + i,
                "name": f"Segment {i}",
                "climb_category": 0,
                "climb_category_desc": "NC",
                "avg_grade": 2.5,
                "distance": 1000,
                "elev_difference": 25,
                "starred": False,
            }
            for i in range(25)
        ]

        explore_result = {"segments": all_segments}

        stub_api.stub_explore_segments_endpoint(explore_result)

        # First page (limit=10)
        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments", {"bounds": "37.77,-122.45,37.80,-122.40", "limit": 10}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["pagination"]["has_more"] is True
        assert len(data["data"]["segments"]) == 10
        assert data["data"]["segments"][0]["id"] == 6000

        # Second page using cursor
        from strava_mcp.pagination import encode_cursor

        cursor = encode_cursor(2, {"bounds": "37.77,-122.45,37.80,-122.40"})

        stub_api.stub_explore_segments_endpoint(explore_result)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments",
                {"bounds": "37.77,-122.45,37.80,-122.40", "cursor": cursor, "limit": 10},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert len(data["data"]["segments"]) == 10
        assert data["data"]["segments"][0]["id"] == 6010  # Offset of 10

    async def test_get_segment_leaderboard_pagination_has_more(self, stub_api):
        """Test leaderboard pagination returns correct metadata."""
        segment_id = 229781

        # Create leaderboard with 51 entries (more than default 50)
        leaderboard_data = {
            **SEGMENT_LEADERBOARD,
            "entry_count": 100,
            "entries": [
                {
                    **SEGMENT_LEADERBOARD["entries"][0],
                    "rank": i + 1,
                    "athlete_name": f"Athlete {i}",
                }
                for i in range(51)  # limit+1
            ],
        }

        stub_api.stub_segment_leaderboard_endpoint(
            segment_id,
            leaderboard_data,
            page=1,
            per_page=51,
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_segment_leaderboard", {"segment_id": segment_id, "limit": 50}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "pagination" in data
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 50
        assert len(data["data"]["entries"]) == 50  # Should trim to limit

    async def test_query_segments_limit_validation(self):
        """Test segment limit validation."""
        # Test limit too high
        async with Client(mcp) as client:
            result = await client.call_tool("query_segments", {"starred_only": True, "limit": 100})

            assert result.is_error is False
            data = json.loads(get_text_content(result))
        assert "error" in data
        assert "limit" in data["error"]["message"].lower()

        # Test efforts_limit too high
        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_segments", {"segment_id": 123, "include_efforts": True, "efforts_limit": 100}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))
        assert "error" in data
        assert "efforts_limit" in data["error"]["message"].lower()
