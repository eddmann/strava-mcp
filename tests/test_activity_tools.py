"""Comprehensive tests for activity tools."""

import json
from datetime import UTC
from unittest.mock import patch

import pytest

from strava_mcp.tools.activities import get_activity_social, query_activities
from tests.fixtures.activity_fixtures import (
    ACTIVITY_COMMENTS,
    ACTIVITY_KUDOERS,
    ACTIVITY_LAPS,
    ACTIVITY_STREAMS,
    ACTIVITY_ZONES,
    DETAILED_ACTIVITY,
    SUMMARY_ACTIVITY,
)
from tests.stubs.strava_api_stub import StravaAPIStubber

# Constants for test IDs
DETAILED_ACTIVITY_ID = DETAILED_ACTIVITY["id"]  # 12345678987654320
SUMMARY_ACTIVITY_ID = SUMMARY_ACTIVITY["id"]  # 154504250376823


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestQueryActivities:
    """Test query_activities tool."""

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_list_recent(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test querying recent activities list."""
        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [SUMMARY_ACTIVITY]
        # Stub paginated responses - return activities for page 1, empty for subsequent pages

        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        result = await query_activities(time_range="recent")
        data = json.loads(result)

        assert "data" in data
        assert "activities" in data["data"]
        assert len(data["data"]["activities"]) == 1
        assert data["data"]["activities"][0]["id"] == SUMMARY_ACTIVITY_ID
        assert data["data"]["activities"][0]["name"] == "Happy Friday"
        assert "distance" in data["data"]["activities"][0]
        assert data["data"]["activities"][0]["distance"]["meters"] == 24931.4
        assert "24.93 km" in data["data"]["activities"][0]["distance"]["formatted"]

        # Check aggregated metrics
        assert "aggregated" in data["data"]
        assert data["data"]["aggregated"]["count"] == 1

        # Check metadata
        assert "metadata" in data
        assert data["metadata"]["query_type"] == "activity_list"
        assert "time_range" in data["metadata"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_single_by_id(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying single activity by ID."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)

        result = await query_activities(activity_id=DETAILED_ACTIVITY_ID)
        data = json.loads(result)

        assert "data" in data
        assert "activity" in data["data"]
        assert data["data"]["activity"]["id"] == DETAILED_ACTIVITY_ID
        assert data["data"]["activity"]["name"] == "Happy Friday"

        # Check both raw and formatted values
        assert "distance" in data["data"]["activity"]
        assert "meters" in data["data"]["activity"]["distance"]
        assert "formatted" in data["data"]["activity"]["distance"]

        # Check metadata
        assert "metadata" in data
        assert data["metadata"]["query_type"] == "single_activity"
        assert data["metadata"]["activity_id"] == DETAILED_ACTIVITY_ID

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_with_laps(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying activity with laps included."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_laps_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_LAPS)

        result = await query_activities(activity_id=DETAILED_ACTIVITY_ID, include_laps=True)
        data = json.loads(result)

        # Debug: print result if there's an error
        if "error" in data:
            print(f"Error in response: {data['error']}")

        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "laps" in data["data"]
        assert len(data["data"]["laps"]) > 0
        assert "lap_number" in data["data"]["laps"][0]
        assert "includes" in data["metadata"]
        assert "laps" in data["metadata"]["includes"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_with_zones(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying activity with zones included."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_zones_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_ZONES)

        result = await query_activities(activity_id=DETAILED_ACTIVITY_ID, include_zones=True)
        data = json.loads(result)

        assert "zones" in data["data"]
        assert "includes" in data["metadata"]
        assert "zones" in data["metadata"]["includes"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_with_streams(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying activity with streams included."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_streams_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_STREAMS)

        result = await query_activities(
            activity_id=DETAILED_ACTIVITY_ID, include_streams="time,heartrate,watts"
        )
        data = json.loads(result)

        # Debug: print result if there's an error
        if "error" in data:
            print(f"Error in response: {data['error']}")

        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "streams" in data["data"]
        assert "includes" in data["metadata"]
        assert any("streams:" in inc for inc in data["metadata"]["includes"])

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_empty_result(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying activities with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activities_endpoint([])

        result = await query_activities(time_range="recent")
        data = json.loads(result)

        assert data["data"]["activities"] == []
        assert data["data"]["aggregated"]["count"] == 0

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test querying activities when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await query_activities()
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_invalid_limit(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test querying activities with invalid limit."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await query_activities(limit=5000)
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]


class TestGetActivitySocial:
    """Test get_activity_social tool."""

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_get_activity_social_with_comments_and_kudos(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting social data with comments and kudos."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_comments_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_COMMENTS)
        stub_api.stub_activity_kudoers_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_KUDOERS)

        result = await get_activity_social(DETAILED_ACTIVITY_ID)
        data = json.loads(result)

        assert "data" in data
        assert "activity" in data["data"]
        assert "comments" in data["data"]
        assert "kudos" in data["data"]

        assert data["data"]["activity"]["id"] == DETAILED_ACTIVITY_ID
        assert len(data["data"]["comments"]) > 0
        assert len(data["data"]["kudos"]) > 0

        # Check comment structure
        comment = data["data"]["comments"][0]
        assert "id" in comment
        assert "athlete" in comment
        assert "text" in comment

        # Check kudos structure
        kudoer = data["data"]["kudos"][0]
        assert "id" in kudoer
        assert "name" in kudoer

        # Check metadata
        assert "metadata" in data
        assert "includes" in data["metadata"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_get_activity_social_comments_only(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting only comments."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_comments_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_COMMENTS)

        result = await get_activity_social(DETAILED_ACTIVITY_ID, include_kudos=False)
        data = json.loads(result)

        assert "comments" in data["data"]
        assert "kudos" not in data["data"]

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_get_activity_social_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting social data for non-existent activity."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/activities/999999", status_code=404)

        result = await get_activity_social(999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]


class TestActivityPagination:
    """Test pagination behavior for activity tools."""

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_pagination_first_page(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test first page of paginated activities returns cursor."""
        from datetime import datetime

        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Create 11 activities (limit+1 to trigger has_more) with recent dates
        now = datetime.now(UTC)
        activities = [
            {
                **SUMMARY_ACTIVITY,
                "id": 1000 + i,
                "name": f"Activity {i}",
                "start_date_local": now.isoformat(),
            }
            for i in range(11)
        ]

        def activities_response(request):
            return Response(200, json=activities)

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        # Request with limit=10 using a wide time range
        result = await query_activities(time_range="90d", limit=10)
        data = json.loads(result)

        # Should have pagination
        assert "pagination" in data
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["returned"] == 10

        # Should only return 10 items
        assert len(data["data"]["activities"]) == 10

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_pagination_second_page(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test using cursor to get second page."""
        from datetime import datetime

        from httpx import Response

        from strava_mcp.pagination import encode_cursor

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Simulate second page having fewer items
        now = datetime.now(UTC)
        activities_page2 = [
            {
                **SUMMARY_ACTIVITY,
                "id": 2000 + i,
                "name": f"Activity {i}",
                "start_date_local": now.isoformat(),
            }
            for i in range(5)
        ]

        def activities_response(request):
            return Response(200, json=activities_page2)

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        # Create cursor for page 2
        cursor = encode_cursor(2, {"time_range": "90d"})

        result = await query_activities(time_range="90d", cursor=cursor, limit=10)
        data = json.loads(result)

        # Should not have more pages
        assert data["pagination"]["has_more"] is False
        assert data["pagination"]["cursor"] is None
        assert data["pagination"]["returned"] == 5

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_pagination_invalid_cursor(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test invalid cursor returns error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await query_activities(cursor="invalid_cursor_string")
        data = json.loads(result)

        assert "error" in data
        assert data["error"]["type"] == "validation_error"
        assert "cursor" in data["error"]["message"].lower()

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_limit_validation(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test limit parameter validation."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Test limit too high
        result = await query_activities(limit=100)
        data = json.loads(result)
        assert "error" in data
        assert "limit" in data["error"]["message"].lower()

        # Test limit too low
        result = await query_activities(limit=0)
        data = json.loads(result)
        assert "error" in data

    @patch("strava_mcp.tools.activities.load_config")
    @patch("strava_mcp.tools.activities.validate_credentials")
    async def test_query_activities_reduced_limit_with_enrichments(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test that enrichments trigger lower default limit."""
        from datetime import datetime

        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Create 6 activities (more than enrichment limit of 5)
        now = datetime.now(UTC)
        activities = [
            {
                **SUMMARY_ACTIVITY,
                "id": 3000 + i,
                "name": f"Activity {i}",
                "start_date_local": now.isoformat(),
            }
            for i in range(6)
        ]

        def activities_response(request):
            return Response(200, json=activities)

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        # Request with enrichments (should default to limit=5)
        # Note: We don't test actual enrichment fetching here, just the limit behavior
        result = await query_activities(time_range="90d", include_laps=True)
        data = json.loads(result)

        # Should use default limit of 5 for enrichments
        assert data["pagination"]["limit"] == 5
        assert len(data["data"]["activities"]) == 5
