"""Comprehensive tests for activity tools."""

import json
from datetime import UTC

import pytest
from fastmcp import Client

from strava_mcp.server import mcp
from tests.fixtures.activity_fixtures import (
    ACTIVITY_COMMENTS,
    ACTIVITY_KUDOERS,
    ACTIVITY_LAPS,
    ACTIVITY_STREAMS,
    ACTIVITY_ZONES,
    DETAILED_ACTIVITY,
    SUMMARY_ACTIVITY,
)
from tests.helpers import get_text_content
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

    async def test_query_activities_list_recent(self, stub_api, respx_mock):
        """Test querying recent activities list."""
        from httpx import Response

        activities = [SUMMARY_ACTIVITY]
        # Stub paginated responses - return activities for page 1, empty for subsequent pages

        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            result = await client.call_tool("query_activities", {"time_range": "recent"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_query_activities_single_by_id(self, stub_api):
        """Test querying single activity by ID."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_activities", {"activity_id": DETAILED_ACTIVITY_ID}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_query_activities_with_laps(self, stub_api):
        """Test querying activity with laps included."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_laps_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_LAPS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_activities",
                {"activity_id": DETAILED_ACTIVITY_ID, "include_laps": True},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "laps" in data["data"]
        assert len(data["data"]["laps"]) > 0
        assert "lap_number" in data["data"]["laps"][0]
        assert "includes" in data["metadata"]
        assert "laps" in data["metadata"]["includes"]

    async def test_query_activities_with_zones(self, stub_api):
        """Test querying activity with zones included."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_zones_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_ZONES)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_activities",
                {"activity_id": DETAILED_ACTIVITY_ID, "include_zones": True},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "zones" in data["data"]
        assert "includes" in data["metadata"]
        assert "zones" in data["metadata"]["includes"]

    async def test_query_activities_with_streams(self, stub_api):
        """Test querying activity with streams included."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_streams_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_STREAMS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_activities",
                {
                    "activity_id": DETAILED_ACTIVITY_ID,
                    "include_streams": "time,heartrate,watts",
                },
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "streams" in data["data"]
        assert "includes" in data["metadata"]
        assert any("streams:" in inc for inc in data["metadata"]["includes"])

    async def test_query_activities_empty_result(self, stub_api):
        """Test querying activities with no results."""
        stub_api.stub_activities_endpoint([])

        async with Client(mcp) as client:
            result = await client.call_tool("query_activities", {"time_range": "recent"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["activities"] == []
        assert data["data"]["aggregated"]["count"] == 0

    async def test_query_activities_invalid_limit(self):
        """Test querying activities with invalid limit."""
        async with Client(mcp) as client:
            result = await client.call_tool("query_activities", {"limit": 5000})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]

    async def test_query_activities_string_limit_coercion(self, stub_api, respx_mock):
        """Test that limit parameter accepts strings and coerces them to integers."""
        from httpx import Response

        activities = [SUMMARY_ACTIVITY]

        def activities_response(request):
            page = request.url.params.get("page", "1")
            if page == "1":
                return Response(200, json=activities)
            return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            # Test with string limit
            result = await client.call_tool(
                "query_activities", {"time_range": "recent", "limit": "1"}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["returned"] == 1

    async def test_query_activities_invalid_string_limit(self):
        """Test querying activities with non-numeric string limit."""
        async with Client(mcp) as client:
            result = await client.call_tool("query_activities", {"limit": "abc"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "abc" in data["error"]["message"]


class TestGetActivitySocial:
    """Test get_activity_social tool."""

    async def test_get_activity_social_with_comments_and_kudos(self, stub_api):
        """Test getting social data with comments and kudos."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_comments_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_COMMENTS)
        stub_api.stub_activity_kudoers_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_KUDOERS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_activity_social", {"activity_id": DETAILED_ACTIVITY_ID}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_get_activity_social_comments_only(self, stub_api):
        """Test getting only comments."""
        stub_api.stub_activity_details_endpoint(DETAILED_ACTIVITY_ID, DETAILED_ACTIVITY)
        stub_api.stub_activity_comments_endpoint(DETAILED_ACTIVITY_ID, ACTIVITY_COMMENTS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_activity_social",
                {"activity_id": DETAILED_ACTIVITY_ID, "include_kudos": False},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "comments" in data["data"]
        assert "kudos" not in data["data"]

    async def test_get_activity_social_not_found(self, stub_api):
        """Test getting social data for non-existent activity."""
        stub_api.stub_error_response("/activities/999999", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("get_activity_social", {"activity_id": 999999})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]


class TestActivityPagination:
    """Test pagination behavior for activity tools."""

    async def test_query_activities_pagination_first_page(self, stub_api, respx_mock):
        """Test first page of paginated activities returns cursor."""
        from datetime import datetime

        from httpx import Response

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

        async with Client(mcp) as client:
            # Request with limit=10 using a wide time range
            result = await client.call_tool("query_activities", {"time_range": "90d", "limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should have pagination
        assert "pagination" in data
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["returned"] == 10

        # Should only return 10 items
        assert len(data["data"]["activities"]) == 10

    async def test_query_activities_pagination_second_page(self, stub_api, respx_mock):
        """Test using cursor to get second page."""
        from datetime import datetime

        from httpx import Response

        from strava_mcp.pagination import encode_cursor

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

        async with Client(mcp) as client:
            result = await client.call_tool(
                "query_activities", {"time_range": "90d", "cursor": cursor, "limit": 10}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should not have more pages
        assert data["pagination"]["has_more"] is False
        assert data["pagination"]["cursor"] is None
        assert data["pagination"]["returned"] == 5

    async def test_query_activities_pagination_invalid_cursor(self):
        """Test invalid cursor returns error."""
        async with Client(mcp) as client:
            result = await client.call_tool("query_activities", {"cursor": "invalid_cursor_string"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert data["error"]["type"] == "validation_error"
        assert "cursor" in data["error"]["message"].lower()

    async def test_query_activities_limit_validation(self):
        """Test limit parameter validation."""
        async with Client(mcp) as client:
            # Test limit too high
            result = await client.call_tool("query_activities", {"limit": 100})

            assert result.is_error is False
            data = json.loads(get_text_content(result))
            assert "error" in data
            assert "limit" in data["error"]["message"].lower()

            # Test limit too low
            result = await client.call_tool("query_activities", {"limit": 0})

            assert result.is_error is False
            data = json.loads(get_text_content(result))
            assert "error" in data

    async def test_query_activities_reduced_limit_with_enrichments(self, stub_api, respx_mock):
        """Test that enrichments trigger lower default limit."""
        from datetime import datetime

        from httpx import Response

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

        async with Client(mcp) as client:
            # Request with enrichments (should default to limit=5)
            # Note: We don't test actual enrichment fetching here, just the limit behavior
            result = await client.call_tool(
                "query_activities", {"time_range": "90d", "include_laps": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should use default limit of 5 for enrichments
        assert data["pagination"]["limit"] == 5
        assert len(data["data"]["activities"]) == 5

    async def test_query_activities_pagination_with_activity_type_filter(
        self, stub_api, respx_mock
    ):
        """Test pagination with activity_type filter applied correctly."""
        from datetime import datetime

        from httpx import Response

        # Create 47 mixed activities (30 Runs, 17 Rides)
        now = datetime.now(UTC)
        activities = []
        for i in range(47):
            activities.append(
                {
                    **SUMMARY_ACTIVITY,
                    "id": 3000 + i,
                    "name": f"Activity {i}",
                    "type": "Run" if i < 30 else "Ride",
                    "start_date_local": now.isoformat(),
                }
            )

        def activities_response(request):
            return Response(200, json=activities)

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            # Request first page of Runs with limit=10
            result = await client.call_tool(
                "query_activities", {"time_range": "90d", "activity_type": "Run", "limit": 10}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should return exactly 10 Runs
        assert len(data["data"]["activities"]) == 10
        assert all(a["type"] == "Run" for a in data["data"]["activities"])

        # Should have pagination (30 total Runs, showing first 10)
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["returned"] == 10

    async def test_query_activities_sparse_type_filtering(self, stub_api, respx_mock):
        """Test pagination with sparse activity type (requires multiple API pages)."""
        from datetime import datetime

        from httpx import Response

        # Create activities where Runs are sparse (1 Run per 10 activities)
        # Total: 300 activities, 30 Runs
        now = datetime.now(UTC)

        def activities_response(request):
            # Simulate pagination - each page returns 200 activities
            page = request.url.params.get("page", "1")
            page_num = int(page)

            if page_num == 1:
                # First 200 activities: 20 Runs
                activities = []
                for i in range(200):
                    activities.append(
                        {
                            **SUMMARY_ACTIVITY,
                            "id": 4000 + i,
                            "name": f"Activity {i}",
                            "type": "Run" if i % 10 == 0 else "Ride",
                            "start_date_local": now.isoformat(),
                        }
                    )
                return Response(200, json=activities)
            elif page_num == 2:
                # Next 100 activities: 10 Runs
                activities = []
                for i in range(100):
                    activities.append(
                        {
                            **SUMMARY_ACTIVITY,
                            "id": 5000 + i,
                            "name": f"Activity {200 + i}",
                            "type": "Run" if i % 10 == 0 else "Ride",
                            "start_date_local": now.isoformat(),
                        }
                    )
                return Response(200, json=activities)
            else:
                return Response(200, json=[])

        respx_mock.get("/athlete/activities").mock(side_effect=activities_response)

        async with Client(mcp) as client:
            # Request first page of 10 Runs - should make multiple API calls to find them
            result = await client.call_tool(
                "query_activities", {"time_range": "90d", "activity_type": "Run", "limit": 10}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should return exactly 10 Runs (from first 100 mixed activities)
        assert len(data["data"]["activities"]) == 10
        assert all(a["type"] == "Run" for a in data["data"]["activities"])

        # Should have pagination (30 total Runs available)
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["returned"] == 10
