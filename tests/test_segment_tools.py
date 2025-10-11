"""Comprehensive tests for segment tools."""

from unittest.mock import patch

import pytest

from strava_mcp.tools.segments import (
    explore_segments,
    get_segment,
    get_segment_effort,
    list_segment_efforts,
    list_starred_segments,
    star_segment,
)
from tests.fixtures.athlete_fixtures import DETAILED_ATHLETE
from tests.fixtures.segment_fixtures import (
    DETAILED_SEGMENT,
    EXPLORE_SEGMENTS_RESPONSE,
    SEGMENT_EFFORT,
    SEGMENT_EFFORTS_LIST,
    SUMMARY_SEGMENT,
)
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestListStarredSegments:
    """Test list_starred_segments tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_starred_segments_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful starred segments list retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        segments = [SUMMARY_SEGMENT]
        stub_api.stub_starred_segments_endpoint(segments)

        result = await list_starred_segments()

        assert "Found 1 starred segments:" in result
        assert "Hawk Hill" in result
        assert "ID: 229781" in result
        assert "Type: Ride" in result
        assert "Distance:" in result
        assert "Avg Grade: 5.7%" in result
        assert "Max Grade: 14.2%" in result
        assert "Climb Category: 1" in result
        assert "Location: San Francisco, CA, United States" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_starred_segments_with_pagination(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test starred segments with pagination."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        segments = [SUMMARY_SEGMENT, {**SUMMARY_SEGMENT, "id": 2, "name": "Second Segment"}]
        stub_api.stub_starred_segments_endpoint(segments)

        result = await list_starred_segments(page=2, per_page=10)

        assert "Found 2 starred segments:" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_starred_segments_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test starred segments with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_starred_segments_endpoint([])

        result = await list_starred_segments()

        assert "No starred segments found." in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_starred_segments_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test starred segments when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await list_starred_segments()

        assert "Error: Strava credentials not configured" in result


class TestExploreSegments:
    """Test explore_segments tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment exploration."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await explore_segments(bounds)

        assert "Found 2 segments:" in result
        assert "Hawk Hill" in result
        assert "Panoramic Climb" in result
        assert "ID: 229781" in result
        assert "Type: Ride" in result
        assert "Climb Category: 1" in result
        assert "Starred: No" in result
        assert "Starred: Yes" in result  # Second segment is starred

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_with_activity_type(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment exploration with activity type filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await explore_segments(bounds, activity_type="riding")

        assert "Found 2 segments:" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_with_climb_category(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment exploration with climb category filters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_explore_segments_endpoint(EXPLORE_SEGMENTS_RESPONSE)

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await explore_segments(bounds, activity_type="riding", min_cat=1, max_cat=3)

        assert "Found 2 segments:" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_invalid_bounds(self, mock_validate, mock_load_config, mock_config):
        """Test segment exploration with invalid bounds format."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        bounds = "37.7,-122.5"  # Only 2 values instead of 4
        result = await explore_segments(bounds)

        assert "Error: bounds must be 4 comma-separated values" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_climb_category_without_riding(self, mock_validate, mock_load_config, mock_config):
        """Test segment exploration with climb category but wrong activity type."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await explore_segments(bounds, activity_type="running", min_cat=1)

        assert "Error: Climb category filters require activity_type='riding'" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_explore_segments_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment exploration with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_explore_segments_endpoint({"segments": []})

        bounds = "37.7,-122.5,37.8,-122.4"
        result = await explore_segments(bounds)

        assert "No segments found in the specified area." in result


class TestGetSegment:
    """Test get_segment tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment details retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_segment_details_endpoint(segment_id, DETAILED_SEGMENT)

        result = await get_segment(segment_id)

        assert "Segment: Hawk Hill" in result
        assert f"ID: {segment_id}" in result
        assert "Activity Type: Ride" in result
        assert "Measurements:" in result
        assert "Distance:" in result
        assert "Avg Grade: 5.7%" in result
        assert "Climb Category: 1" in result
        assert "Location:" in result
        assert "City: San Francisco" in result
        assert "Popularity:" in result
        assert "Total Efforts: 309974" in result
        assert "Total Athletes: 30623" in result
        assert "Stars: 2428" in result
        assert "Starred by you: No" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_hazardous(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment details with hazardous flag."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        hazardous_segment = {**DETAILED_SEGMENT, "hazardous": True}
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_segment_details_endpoint(segment_id, hazardous_segment)

        result = await get_segment(segment_id)

        assert "This segment has been flagged as hazardous" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment details with non-existent segment."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 999999
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_error_response(f"/segments/{segment_id}", status_code=404)

        result = await get_segment(segment_id)

        assert "Error:" in result


class TestStarSegment:
    """Test star_segment tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_star_segment_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment starring."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        starred_segment = {**DETAILED_SEGMENT, "starred": True}
        stub_api.stub_star_segment_endpoint(segment_id, starred_segment)

        result = await star_segment(segment_id, starred=True)

        assert "Successfully starred segment: Hawk Hill" in result
        assert f"ID: {segment_id}" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_unstar_segment_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment unstarring."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        unstarred_segment = {**DETAILED_SEGMENT, "starred": False}
        stub_api.stub_star_segment_endpoint(segment_id, unstarred_segment)

        result = await star_segment(segment_id, starred=False)

        assert "Successfully unstarred segment: Hawk Hill" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_star_segment_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test starring non-existent segment."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 999999
        stub_api.stub_error_response(f"/segments/{segment_id}/starred", method="PUT", status_code=404)

        result = await star_segment(segment_id)

        assert "Error:" in result


class TestGetSegmentEffort:
    """Test get_segment_effort tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_effort_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment effort retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        effort_id = 1234556789
        stub_api.stub_segment_effort_endpoint(effort_id, SEGMENT_EFFORT)

        result = await get_segment_effort(effort_id)

        assert "Segment Effort: Hawk Hill" in result
        assert f"Effort ID: {effort_id}" in result
        assert "Date:" in result
        assert "Segment: Hawk Hill (ID: 229781)" in result
        assert "Performance:" in result
        assert "Elapsed Time:" in result
        assert "Moving Time:" in result
        assert "Heart Rate:" in result
        assert "Average: 155 bpm" in result
        assert "Power:" in result
        assert "Average: 250 W" in result
        assert "Cadence: 75 rpm" in result
        assert "PR Rank: 1" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_effort_with_kom_rank(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment effort with KOM rank."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        effort_id = 123
        effort_with_kom = {**SEGMENT_EFFORT, "id": effort_id, "kom_rank": 3}
        stub_api.stub_segment_effort_endpoint(effort_id, effort_with_kom)

        result = await get_segment_effort(effort_id)

        assert "KOM Rank: 3" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_get_segment_effort_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment effort with non-existent effort."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        effort_id = 999999
        stub_api.stub_error_response(f"/segment_efforts/{effort_id}", status_code=404)

        result = await get_segment_effort(effort_id)

        assert "Error:" in result


class TestListSegmentEfforts:
    """Test list_segment_efforts tool."""

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_segment_efforts_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful segment efforts list retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_efforts_endpoint(segment_id, SEGMENT_EFFORTS_LIST)

        result = await list_segment_efforts(segment_id)

        assert f"Found {len(SEGMENT_EFFORTS_LIST)} efforts for segment {segment_id}:" in result
        assert "1. Hawk Hill" in result
        assert "Effort ID: 123456789" in result
        assert "Date:" in result
        assert "Time:" in result
        assert "Avg HR: 145 bpm" in result
        assert "Avg Power: 220 W" in result
        assert "PR Rank: 2" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_segment_efforts_with_date_filters(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment efforts with date filters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_efforts_endpoint(segment_id, SEGMENT_EFFORTS_LIST)

        result = await list_segment_efforts(
            segment_id,
            start_date="2007-01-01",
            end_date="2007-12-31"
        )

        assert "Found 1 efforts" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_segment_efforts_invalid_date(self, mock_validate, mock_load_config, mock_config):
        """Test segment efforts with invalid date format."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        result = await list_segment_efforts(segment_id, start_date="invalid-date")

        assert "Error: Invalid date format" in result

    @patch('strava_mcp.tools.segments.load_config')
    @patch('strava_mcp.tools.segments.validate_credentials')
    async def test_list_segment_efforts_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test segment efforts with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        segment_id = 229781
        stub_api.stub_segment_efforts_endpoint(segment_id, [])

        result = await list_segment_efforts(segment_id)

        assert "No efforts found for this segment." in result
