"""Comprehensive tests for segment tools."""

import json
from unittest.mock import patch

import pytest

from strava_mcp.tools.segments import (
    get_segment_leaderboard,
    query_segments,
    star_segment,
)
from tests.fixtures.segment_fixtures import (
    DETAILED_SEGMENT,
    EXPLORE_SEGMENTS_RESPONSE,
    SEGMENT_EFFORTS_LIST,
    SEGMENT_LEADERBOARD,
    SUMMARY_SEGMENT,
)
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestQuerySegments:
    """Test query_segments tool."""

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_single_segment(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying single segment by ID."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)

        result = await query_segments(segment_id=segment_id)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_with_efforts(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying segment with efforts history."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)
        stub_api.stub_segment_efforts_endpoint(segment_id, SEGMENT_EFFORTS_LIST)

        result = await query_segments(segment_id=segment_id, include_efforts=True)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_starred_list(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying starred segments."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segments = [SUMMARY_SEGMENT, {**SUMMARY_SEGMENT, "id": 2, "name": "Segment 2"}]
        stub_api.stub_starred_segments_endpoint(segments)

        result = await query_segments(starred_only=True)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_starred_empty(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying starred segments with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_starred_segments_endpoint([])

        result = await query_segments(starred_only=True)
        data = json.loads(result)

        assert data["data"]["count"] == 0
        assert data["data"]["segments"] == []

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_explore(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test exploring segments in geographic area."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await query_segments(bounds=bounds)
        data = json.loads(result)

        # Debug: print result if there's an error
        if "error" in data:
            print(f"Error in response: {data['error']}")

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

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_explore_with_activity_type(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test exploring segments with activity type filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await query_segments(bounds=bounds, activity_type="riding")
        data = json.loads(result)

        assert data["data"]["count"] > 0
        assert data["metadata"]["activity_type"] == "riding"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_explore_with_climb_categories(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test exploring segments with climb category filters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await query_segments(
            bounds=bounds, activity_type="riding", min_category=1, max_category=3
        )
        data = json.loads(result)

        assert data["data"]["count"] > 0
        assert data["metadata"]["min_category"] == 1
        assert data["metadata"]["max_category"] == 3

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_explore_invalid_bounds(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test exploring segments with invalid bounds format."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        bounds = "37.7,-122.5"  # Only 2 values instead of 4
        result = await query_segments(bounds=bounds)
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_default_starred(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test that default query returns starred segments."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segments = [SUMMARY_SEGMENT]
        stub_api.stub_starred_segments_endpoint(segments)

        result = await query_segments()
        data = json.loads(result)

        assert data["metadata"]["query_type"] == "starred_segments"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_with_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying segments with custom limit."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segments = [SUMMARY_SEGMENT for _ in range(50)]
        stub_api.stub_starred_segments_endpoint(segments)

        result = await query_segments(starred_only=True, limit=10)
        data = json.loads(result)

        # Should return max 10 segments
        assert len(data["data"]["segments"]) <= 10

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_with_feet_units(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying segments with feet/miles units."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)

        result = await query_segments(segment_id=segment_id, unit="feet")
        data = json.loads(result)

        # Check that formatted values use miles/feet
        assert "mi" in data["data"]["segment"]["distance"]["formatted"]
        assert "ft" in data["data"]["segment"]["elevation_high"]["formatted"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying non-existent segment."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/segments/999999", status_code=404)

        result = await query_segments(segment_id=999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_query_segments_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test querying segments when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await query_segments()
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]


class TestStarSegment:
    """Test star_segment tool."""

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_star_segment_success(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test successful segment starring."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        starred_segment = {**DETAILED_SEGMENT, "starred": True}
        stub_api.stub_star_segment_endpoint(segment_id, starred_segment)

        result = await star_segment(segment_id, starred=True)
        data = json.loads(result)

        # Check structure
        assert "data" in data
        assert data["data"]["segment_id"] == segment_id
        assert data["data"]["starred"] is True
        assert data["data"]["success"] is True

        # Check metadata
        assert "metadata" in data

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_unstar_segment_success(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test successful segment unstarring."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        unstarred_segment = {**DETAILED_SEGMENT, "starred": False}
        stub_api.stub_star_segment_endpoint(segment_id, unstarred_segment)

        result = await star_segment(segment_id, starred=False)
        data = json.loads(result)

        assert data["data"]["segment_id"] == segment_id
        assert data["data"]["starred"] is False
        assert data["data"]["success"] is True

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_star_segment_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test starring non-existent segment."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/segments/999999/starred", method="PUT", status_code=404)

        result = await star_segment(999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_star_segment_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test starring segment when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await star_segment(229781)
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_star_segment_rate_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test starring segment with rate limit error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/segments/229781/starred", method="PUT", status_code=429)

        result = await star_segment(229781)
        data = json.loads(result)

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]


class TestGetSegmentLeaderboard:
    """Test get_segment_leaderboard tool."""

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_success(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test successful segment leaderboard retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD)

        result = await get_segment_leaderboard(segment_id)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_gender_filter(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with gender filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, gender="M")

        result = await get_segment_leaderboard(segment_id, gender="M")
        data = json.loads(result)

        assert data["metadata"]["filters"]["gender"] == "M"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_age_group(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with age group filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, age_group="25_34"
        )

        result = await get_segment_leaderboard(segment_id, age_group="25_34")
        data = json.loads(result)

        assert data["metadata"]["filters"]["age_group"] == "25_34"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_weight_class(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with weight class filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, weight_class="75_84"
        )

        result = await get_segment_leaderboard(segment_id, weight_class="75_84")
        data = json.loads(result)

        assert data["metadata"]["filters"]["weight_class"] == "75_84"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_following(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with following filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, following=True)

        result = await get_segment_leaderboard(segment_id, following=True)
        data = json.loads(result)

        assert data["metadata"]["filters"]["following"] is True

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_club(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with club filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        club_id = 12345
        stub_api.stub_segment_leaderboard_endpoint(segment_id, SEGMENT_LEADERBOARD, club_id=club_id)

        result = await get_segment_leaderboard(segment_id, club_id=club_id)
        data = json.loads(result)

        assert data["metadata"]["filters"]["club_id"] == club_id

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_date_range(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with date range filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, date_range="this_year"
        )

        result = await get_segment_leaderboard(segment_id, date_range="this_year")
        data = json.loads(result)

        assert data["metadata"]["filters"]["date_range"] == "this_year"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_multiple_filters(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with multiple filters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id,
            SEGMENT_LEADERBOARD,
            gender="F",
            age_group="35_44",
            date_range="this_month",
        )

        result = await get_segment_leaderboard(
            segment_id, gender="F", age_group="35_44", date_range="this_month"
        )
        data = json.loads(result)

        filters = data["metadata"]["filters"]
        assert filters["gender"] == "F"
        assert filters["age_group"] == "35_44"
        assert filters["date_range"] == "this_month"

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_with_pagination(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with pagination."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_leaderboard_endpoint(
            segment_id, SEGMENT_LEADERBOARD, page=2, per_page=10
        )

        result = await get_segment_leaderboard(segment_id, page=2, per_page=10)
        data = json.loads(result)

        assert data["metadata"]["page"] == 2
        assert data["metadata"]["per_page"] == 10

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_empty(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with no entries."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        empty_leaderboard = {
            "entry_count": 0,
            "effort_count": 0,
            "kom_type": "kom",
            "entries": [],
        }
        stub_api.stub_segment_leaderboard_endpoint(segment_id, empty_leaderboard)

        result = await get_segment_leaderboard(segment_id)
        data = json.loads(result)

        assert data["data"]["entry_count"] == 0
        assert data["data"]["entries"] == []

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test segment leaderboard with non-existent segment."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/segments/999999/leaderboard", status_code=404)

        result = await get_segment_leaderboard(999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]

    @patch("strava_mcp.tools.segments.load_config")
    @patch("strava_mcp.tools.segments.validate_credentials")
    async def test_get_segment_leaderboard_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test segment leaderboard when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_segment_leaderboard(229781)
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]
