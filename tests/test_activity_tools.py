"""Comprehensive tests for activity tools."""

from unittest.mock import patch

import pytest

from strava_mcp.tools.activities import (
    get_activity_details,
    get_activity_laps,
    get_activity_streams,
    get_all_activities,
    get_recent_activities,
)
from tests.fixtures.activity_fixtures import (
    ACTIVITY_LAPS,
    ACTIVITY_STREAMS,
    DETAILED_ACTIVITY,
    SUMMARY_ACTIVITY,
)
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestGetRecentActivities:
    """Test get_recent_activities tool."""

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_recent_activities_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful recent activities retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [SUMMARY_ACTIVITY]
        stub_api.stub_activities_endpoint(activities)

        result = await get_recent_activities()

        assert "Found 1 recent activities:" in result
        assert "Happy Friday" in result
        assert "ID: 154504250376823" in result
        assert "Type: Ride" in result
        assert "24.93 km" in result  # distance formatted

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_recent_activities_with_pagination(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test recent activities with pagination parameters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [SUMMARY_ACTIVITY, {**SUMMARY_ACTIVITY, "id": 2, "name": "Morning Ride"}]
        stub_api.stub_activities_endpoint(activities, page=2, per_page=10)

        result = await get_recent_activities(page=2, per_page=10)

        assert "Found 2 recent activities:" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_recent_activities_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test recent activities with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activities_endpoint([])

        result = await get_recent_activities()

        assert "No activities found." in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_recent_activities_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test recent activities when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_recent_activities()

        assert "Error: Strava credentials not configured" in result


class TestGetAllActivities:
    """Test get_all_activities tool."""

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_all_activities_success(self, mock_validate, mock_load_config, mock_config, respx_mock):
        """Test successful all activities retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Mock paginated responses
        page_1 = [SUMMARY_ACTIVITY, {**SUMMARY_ACTIVITY, "id": 2, "name": "Activity 2"}]
        page_2 = [{**SUMMARY_ACTIVITY, "id": 3, "name": "Activity 3"}]
        page_3 = []  # Empty page to stop pagination

        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 1}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=page_1)
        )
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 2}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=page_2)
        )
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 3}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=page_3)
        )

        result = await get_all_activities()

        assert "Found 3 activities:" in result
        assert "Happy Friday" in result
        assert "Activity 2" in result
        assert "Activity 3" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_all_activities_with_type_filter(self, mock_validate, mock_load_config, mock_config, respx_mock):
        """Test all activities with activity type filter."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [
            {**SUMMARY_ACTIVITY, "id": 1, "type": "Ride", "sport_type": "Ride"},
            {**SUMMARY_ACTIVITY, "id": 2, "type": "Run", "sport_type": "Run", "name": "Morning Run"},
        ]
        # Mock page 1 with activities, page 2 empty to stop pagination
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 1}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=activities)
        )
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 2}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=[])
        )

        result = await get_all_activities(activity_type="Run")

        assert "Found 1 activities:" in result
        assert "Morning Run" in result
        assert "Happy Friday" not in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_all_activities_with_date_filters(self, mock_validate, mock_load_config, mock_config, respx_mock):
        """Test all activities with date filters."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [SUMMARY_ACTIVITY]
        # Mock page 1 with activities, page 2 empty to stop pagination
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 1}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=activities)
        )
        respx_mock.get("/athlete/activities", params={"per_page": 30, "page": 2}).mock(
            return_value=pytest.importorskip("httpx").Response(200, json=[])
        )

        result = await get_all_activities(after="2018-01-01", before="2018-12-31")

        assert "Found 1 activities:" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_all_activities_invalid_date(self, mock_validate, mock_load_config, mock_config):
        """Test all activities with invalid date format."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await get_all_activities(after="invalid-date")

        assert "Error: Invalid date format" in result


class TestGetActivityDetails:
    """Test get_activity_details tool."""

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_details_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful activity details retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 12345678987654320
        stub_api.stub_activity_details_endpoint(activity_id, DETAILED_ACTIVITY)

        result = await get_activity_details(activity_id)

        assert "Activity: Happy Friday" in result
        assert f"ID: {activity_id}" in result
        assert "Type: Ride" in result
        assert "28.10 km" in result
        assert "Distance & Time:" in result
        assert "Speed:" in result
        assert "Elevation:" in result
        assert "Kudos: 19" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_details_with_heartrate(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity details with heart rate data."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        activity_with_hr = {
            **DETAILED_ACTIVITY,
            "id": activity_id,
            "has_heartrate": True,
            "average_heartrate": 150.0,
            "max_heartrate": 180
        }
        stub_api.stub_activity_details_endpoint(activity_id, activity_with_hr)

        result = await get_activity_details(activity_id)

        assert "Heart Rate:" in result
        assert "Average: 150 bpm" in result
        assert "Max: 180 bpm" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_details_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity details with non-existent activity."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 999999
        stub_api.stub_error_response(f"/activities/{activity_id}", status_code=404)

        result = await get_activity_details(activity_id)

        assert "Error:" in result


class TestGetActivityStreams:
    """Test get_activity_streams tool."""

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_streams_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful activity streams retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        stub_api.stub_activity_streams_endpoint(activity_id, ACTIVITY_STREAMS)

        result = await get_activity_streams(activity_id)

        assert f"Activity {activity_id} Streams:" in result
        assert "TIME:" in result
        assert "DISTANCE:" in result
        assert "ALTITUDE:" in result
        assert "VELOCITY_SMOOTH:" in result
        assert "HEARTRATE:" in result
        assert "WATTS:" in result
        assert "Data points:" in result
        assert "Normalized Power:" in result  # Special calculation for watts

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_streams_with_specific_types(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity streams with specific stream types."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        limited_streams = {
            "heartrate": ACTIVITY_STREAMS["heartrate"],
            "watts": ACTIVITY_STREAMS["watts"]
        }
        stub_api.stub_activity_streams_endpoint(activity_id, limited_streams)

        result = await get_activity_streams(activity_id, streams="heartrate,watts")

        assert "HEARTRATE:" in result
        assert "WATTS:" in result
        assert "DISTANCE:" not in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_streams_with_max_results(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity streams with max_results limit."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        stub_api.stub_activity_streams_endpoint(activity_id, ACTIVITY_STREAMS)

        result = await get_activity_streams(activity_id, max_results=3)

        # Should only show first 3 data points
        assert "Data points: 3" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_streams_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity streams with no data."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        stub_api.stub_activity_streams_endpoint(activity_id, {})

        result = await get_activity_streams(activity_id)

        assert "No stream data available for this activity." in result


class TestGetActivityLaps:
    """Test get_activity_laps tool."""

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_laps_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful activity laps retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 12345678987654320
        stub_api.stub_activity_laps_endpoint(activity_id, ACTIVITY_LAPS)

        result = await get_activity_laps(activity_id)

        assert f"Found {len(ACTIVITY_LAPS)} laps for activity {activity_id}:" in result
        assert "Lap 1 - Lap 1" in result
        assert "Lap 2 - Lap 2" in result
        assert "8.05 km" in result  # First lap distance
        assert "Avg Speed:" in result
        assert "Avg Power:" in result
        assert "Avg Cadence:" in result
        assert "--- Raw Lap Data (JSON) ---" in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_laps_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity laps with no laps."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 123
        stub_api.stub_activity_laps_endpoint(activity_id, [])

        result = await get_activity_laps(activity_id)

        assert "No laps found for this activity." in result

    @patch('strava_mcp.tools.activities.load_config')
    @patch('strava_mcp.tools.activities.validate_credentials')
    async def test_get_activity_laps_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test activity laps with non-existent activity."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activity_id = 999999
        stub_api.stub_error_response(f"/activities/{activity_id}/laps", status_code=404)

        result = await get_activity_laps(activity_id)

        assert "Error:" in result
