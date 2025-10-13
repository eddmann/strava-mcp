"""Tests for analysis tools."""

import json
from unittest.mock import patch

import pytest

from strava_mcp.tools.analysis import (
    analyze_training,
    compare_activities,
    find_similar_activities,
)
from tests.fixtures.activity_fixtures import DETAILED_ACTIVITY, SUMMARY_ACTIVITY
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestAnalyzeTraining:
    """Test analyze_training tool."""

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_analyze_training_success(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test successful training analysis."""
        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Create multiple activities for analysis
        activities = [SUMMARY_ACTIVITY for _ in range(5)]

        # Stub paginated responses
        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        result = await analyze_training(period="30d")
        data = json.loads(result)

        # Check structure
        assert "data" in data
        assert "period" in data["data"]
        assert "summary" in data["data"]
        assert "by_activity_type" in data["data"]
        assert "trends" in data["data"]

        # Check period info
        assert data["data"]["period"]["description"] == "Last 30 days"
        assert "days" in data["data"]["period"]

        # Check summary metrics
        assert data["data"]["summary"]["total_activities"] == 5
        assert "total_distance" in data["data"]["summary"]
        assert "total_time" in data["data"]["summary"]
        assert "total_elevation" in data["data"]["summary"]
        assert "averages" in data["data"]["summary"]

        # Check both raw and formatted values
        assert "meters" in data["data"]["summary"]["total_distance"]
        assert "formatted" in data["data"]["summary"]["total_distance"]

        # Check activity type distribution
        assert len(data["data"]["by_activity_type"]) > 0
        assert "type" in data["data"]["by_activity_type"][0]
        assert "count" in data["data"]["by_activity_type"][0]
        assert "percentage" in data["data"]["by_activity_type"][0]

        # Check weekly trends
        assert "weekly" in data["data"]["trends"]

        # Check analysis insights
        assert "analysis" in data
        assert "insights" in data["analysis"]

        # Check metadata
        assert "metadata" in data
        assert "period" in data["metadata"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_analyze_training_empty(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test training analysis with no activities."""
        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        respx_mock.get("/athlete/activities").mock(return_value=Response(200, json=[]))

        result = await analyze_training(period="7d")
        data = json.loads(result)

        assert data["data"]["summary"]["total_activities"] == 0
        assert "message" in data["data"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_analyze_training_with_type_filter(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test training analysis filtered by activity type."""
        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        activities = [SUMMARY_ACTIVITY for _ in range(3)]

        # Stub paginated responses
        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        result = await analyze_training(period="30d", activity_type="Run")
        data = json.loads(result)

        assert "metadata" in data
        assert data["metadata"].get("activity_type") == "Run"


class TestCompareActivities:
    """Test compare_activities tool."""

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_compare_activities_success(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test successful activity comparison."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Stub two activities
        activity1 = {**DETAILED_ACTIVITY, "id": 1}
        activity2 = {**DETAILED_ACTIVITY, "id": 2, "distance": 30000}

        stub_api.stub_activity_details_endpoint(1, activity1)
        stub_api.stub_activity_details_endpoint(2, activity2)

        result = await compare_activities("1,2")
        data = json.loads(result)

        # Check structure
        assert "data" in data
        assert "activities" in data["data"]
        assert "comparison" in data["data"]

        # Check activities
        assert len(data["data"]["activities"]) == 2
        assert data["data"]["activities"][0]["id"] == 1
        assert data["data"]["activities"][1]["id"] == 2

        # Check comparison has structured data
        assert "distance" in data["data"]["comparison"]
        assert "longest" in data["data"]["comparison"]["distance"]
        assert "shortest" in data["data"]["comparison"]["distance"]

        # Check metadata
        assert "metadata" in data
        assert "activity_ids" in data["metadata"]
        assert data["metadata"]["activity_ids"] == [1, 2]

        # Check analysis
        assert "analysis" in data
        assert "insights" in data["analysis"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_compare_activities_too_few(self, mock_validate, mock_load_config, mock_config):
        """Test comparison with too few activities."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await compare_activities("1")
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "at least 2" in data["error"]["message"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_compare_activities_too_many(self, mock_validate, mock_load_config, mock_config):
        """Test comparison with too many activities."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await compare_activities("1,2,3,4,5,6")
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "up to 5" in data["error"]["message"]


class TestFindSimilarActivities:
    """Test find_similar_activities tool."""

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_find_similar_activities_success(
        self, mock_validate, mock_load_config, mock_config, stub_api, respx_mock
    ):
        """Test finding similar activities."""
        from httpx import Response

        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Reference activity
        reference = {**DETAILED_ACTIVITY, "id": 1}
        stub_api.stub_activity_details_endpoint(1, reference)

        # Similar activities
        similar1 = {**SUMMARY_ACTIVITY, "id": 2, "distance": 25000}
        similar2 = {**SUMMARY_ACTIVITY, "id": 3, "distance": 24500}
        activities = [similar1, similar2]

        # Stub paginated responses
        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        result = await find_similar_activities(1, criteria="type,distance")
        data = json.loads(result)

        # Check structure
        assert "data" in data
        assert "reference_activity" in data["data"]
        assert "similar_activities" in data["data"]
        assert "count" in data["data"]

        # Check reference activity
        assert data["data"]["reference_activity"]["id"] == 1

        # Check similar activities structure
        if len(data["data"]["similar_activities"]) > 0:
            similar = data["data"]["similar_activities"][0]
            assert "activity" in similar
            assert "similarity_score" in similar
            assert "differences" in similar
            assert 0 <= similar["similarity_score"] <= 1

        # Check metadata
        assert "metadata" in data
        assert data["metadata"]["reference_activity_id"] == 1
        assert "type" in data["metadata"]["criteria"]
        assert "distance" in data["metadata"]["criteria"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_find_similar_activities_invalid_criteria(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test with invalid similarity criteria."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await find_similar_activities(1, criteria="invalid,type")
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "Invalid criteria" in data["error"]["message"]

    @patch("strava_mcp.tools.analysis.load_config")
    @patch("strava_mcp.tools.analysis.validate_credentials")
    async def test_find_similar_activities_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test with non-existent reference activity."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/activities/999999", status_code=404)

        result = await find_similar_activities(999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]
