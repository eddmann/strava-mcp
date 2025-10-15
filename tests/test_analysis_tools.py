"""Tests for analysis tools."""

import json

import pytest
from fastmcp import Client

from strava_mcp.server import mcp
from tests.fixtures.activity_fixtures import DETAILED_ACTIVITY, SUMMARY_ACTIVITY
from tests.helpers import get_text_content
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestAnalyzeTraining:
    """Test analyze_training tool."""

    async def test_analyze_training_success(self, stub_api, respx_mock):
        """Test successful training analysis."""
        from httpx import Response

        # Create multiple activities for analysis
        activities = [SUMMARY_ACTIVITY for _ in range(5)]

        # Stub paginated responses
        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            result = await client.call_tool("analyze_training", {"period": "30d"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_analyze_training_empty(self, stub_api, respx_mock):
        """Test training analysis with no activities."""
        from httpx import Response

        respx_mock.get("/athlete/activities").mock(return_value=Response(200, json=[]))

        async with Client(mcp) as client:
            result = await client.call_tool("analyze_training", {"period": "7d"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["summary"]["total_activities"] == 0
        assert "message" in data["data"]

    async def test_analyze_training_with_type_filter(self, stub_api, respx_mock):
        """Test training analysis filtered by activity type."""
        from httpx import Response

        activities = [SUMMARY_ACTIVITY for _ in range(3)]

        # Stub paginated responses
        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "analyze_training", {"period": "30d", "activity_type": "Run"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "metadata" in data
        assert data["metadata"].get("activity_type") == "Run"


class TestCompareActivities:
    """Test compare_activities tool."""

    async def test_compare_activities_success(self, stub_api):
        """Test successful activity comparison."""
        # Stub two activities
        activity1 = {**DETAILED_ACTIVITY, "id": 1}
        activity2 = {**DETAILED_ACTIVITY, "id": 2, "distance": 30000}

        stub_api.stub_activity_details_endpoint(1, activity1)
        stub_api.stub_activity_details_endpoint(2, activity2)

        async with Client(mcp) as client:
            result = await client.call_tool("compare_activities", {"activity_ids": "1,2"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_compare_activities_too_few(self):
        """Test comparison with too few activities."""
        async with Client(mcp) as client:
            result = await client.call_tool("compare_activities", {"activity_ids": "1"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "at least 2" in data["error"]["message"]

    async def test_compare_activities_too_many(self):
        """Test comparison with too many activities."""
        async with Client(mcp) as client:
            result = await client.call_tool("compare_activities", {"activity_ids": "1,2,3,4,5,6"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "up to 5" in data["error"]["message"]


class TestFindSimilarActivities:
    """Test find_similar_activities tool."""

    async def test_find_similar_activities_success(self, stub_api, respx_mock):
        """Test finding similar activities."""
        from httpx import Response

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

        async with Client(mcp) as client:
            result = await client.call_tool(
                "find_similar_activities", {"activity_id": 1, "criteria": "type,distance"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert "reference_activity" in data["data"]
        assert "similar_activities" in data["data"]
        assert "count" in data["data"]

        # Check reference activity
        assert data["data"]["reference_activity"]["id"] == 1

        # Check similar activities structure
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

    async def test_find_similar_activities_invalid_criteria(self):
        """Test with invalid similarity criteria."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "find_similar_activities", {"activity_id": 1, "criteria": "invalid,type"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "Invalid criteria" in data["error"]["message"]

    async def test_find_similar_activities_not_found(self, stub_api):
        """Test with non-existent reference activity."""
        stub_api.stub_error_response("/activities/999999", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "find_similar_activities", {"activity_id": 999999, "criteria": "type,distance"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]
