"""Comprehensive tests for route tools."""

import json

import pytest
from fastmcp import Client

from tests.fixtures.athlete_fixtures import DETAILED_ATHLETE
from tests.fixtures.route_fixtures import GPX_DATA, ROUTE, ROUTE_LIST, TCX_DATA
from tests.helpers import get_text_content
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestQueryRoutes:
    """Test query_routes tool."""

    async def test_query_routes_single_route(self, stub_api, mcp):
        """Test querying single route by ID."""
        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"route_id": route_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert "route" in data["data"]
        assert data["data"]["route"]["id"] == route_id
        assert data["data"]["route"]["name"] == "Morning Commute"
        assert data["data"]["route"]["description"] == "My daily ride to work"

        # Check structured metrics
        assert "meters" in data["data"]["route"]["distance"]
        assert "formatted" in data["data"]["route"]["distance"]
        assert "meters" in data["data"]["route"]["elevation_gain"]
        assert "formatted" in data["data"]["route"]["elevation_gain"]

        # Check optional fields
        assert "type" in data["data"]["route"]
        assert "private" in data["data"]["route"]
        assert "starred" in data["data"]["route"]

        # Check metadata
        assert data["metadata"]["query_type"] == "single_route"
        assert data["metadata"]["route_id"] == route_id

    async def test_query_routes_with_segments(self, stub_api, mcp):
        """Test querying route with segments."""
        route_id = 987654
        route_with_segments = {
            **ROUTE,
            "segments": [
                {
                    "id": 1,
                    "name": "Segment 1",
                    "distance": 1000,
                    "avg_grade": 5.0,
                    "climb_category": 1,
                    "resource_state": 2,
                    "activity_type": "Ride",
                    "average_grade": 5.0,
                    "maximum_grade": 8.0,
                    "elevation_high": 100.0,
                    "elevation_low": 50.0,
                    "private": False,
                },
                {
                    "id": 2,
                    "name": "Segment 2",
                    "distance": 2000,
                    "avg_grade": 3.5,
                    "climb_category": 2,
                    "resource_state": 2,
                    "activity_type": "Ride",
                    "average_grade": 3.5,
                    "maximum_grade": 6.0,
                    "elevation_high": 150.0,
                    "elevation_low": 100.0,
                    "private": False,
                },
            ],
        }
        stub_api.stub_route_details_endpoint(route_id, route_with_segments)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"route_id": route_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "data" in data, f"Expected 'data' key, got: {data.keys()}"
        assert "segments" in data["data"]["route"]
        assert len(data["data"]["route"]["segments"]) == 2

        # Check segment structure
        segment = data["data"]["route"]["segments"][0]
        assert "id" in segment
        assert "name" in segment
        assert "distance" in segment
        assert "meters" in segment["distance"]
        assert "formatted" in segment["distance"]
        assert "avg_grade" in segment
        assert "percent" in segment["avg_grade"]
        assert "formatted" in segment["avg_grade"]

    async def test_query_routes_list(self, stub_api, mcp):
        """Test listing all routes."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "routes" in data["data"]
        assert "count" in data["data"]
        assert data["data"]["count"] == 2
        assert len(data["data"]["routes"]) == 2

        # Check route structure
        route = data["data"]["routes"][0]
        assert "id" in route
        assert "name" in route
        assert "distance" in route
        assert "meters" in route["distance"]
        assert "formatted" in route["distance"]
        assert "elevation_gain" in route
        assert "type" in route
        assert "starred" in route

        # Check metadata
        assert data["metadata"]["query_type"] == "list_routes"

    async def test_query_routes_default_list(self, stub_api, mcp):
        """Test that default query lists routes."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["metadata"]["query_type"] == "list_routes"
        assert "routes" in data["data"]

    async def test_query_routes_with_limit(self, stub_api, mcp):
        """Test querying routes with custom limit."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        routes = [ROUTE_LIST[0] for _ in range(50)]
        stub_api.stub_routes_endpoint(athlete_id, routes)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should return max 10 routes
        assert len(data["data"]["routes"]) <= 10

    async def test_query_routes_with_feet_units(self, stub_api, mcp):
        """Test querying routes with feet/miles units."""
        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"route_id": route_id, "unit": "feet"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check that formatted values use miles/feet
        assert "mi" in data["data"]["route"]["distance"]["formatted"]
        assert "ft" in data["data"]["route"]["elevation_gain"]["formatted"]

    async def test_query_routes_empty_list(self, stub_api, mcp):
        """Test querying routes with no results."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, [])

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["count"] == 0
        assert data["data"]["routes"] == []

    async def test_query_routes_not_found(self, stub_api, mcp):
        """Test querying non-existent route."""
        stub_api.stub_error_response("/routes/999999", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"route_id": 999999})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]

    async def test_query_routes_rate_limit(self, stub_api, mcp):
        """Test querying routes with rate limit error."""
        stub_api.stub_error_response("/routes/987654", status_code=429)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"route_id": 987654})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]


class TestExportRoute:
    """Test export_route tool."""

    async def test_export_route_gpx(self, stub_api, mcp):
        """Test successful GPX export."""
        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": route_id, "format": "gpx"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert "data" in data
        assert data["data"]["route_id"] == route_id
        assert data["data"]["format"] == "gpx"
        assert data["data"]["content"] == GPX_DATA
        assert data["data"]["filename"] == f"route_{route_id}.gpx"
        assert "size_bytes" in data["data"]

        # Check metadata
        assert data["metadata"]["export_format"] == "gpx"
        assert data["metadata"]["route_id"] == route_id

    async def test_export_route_tcx(self, stub_api, mcp):
        """Test successful TCX export."""
        route_id = 987654
        stub_api.stub_route_export_tcx_endpoint(route_id, TCX_DATA)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": route_id, "format": "tcx"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check structure
        assert data["data"]["route_id"] == route_id
        assert data["data"]["format"] == "tcx"
        assert data["data"]["content"] == TCX_DATA
        assert data["data"]["filename"] == f"route_{route_id}.tcx"

        # Check metadata
        assert data["metadata"]["export_format"] == "tcx"

    async def test_export_route_default_gpx(self, stub_api, mcp):
        """Test that default format is GPX."""
        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": route_id})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert data["data"]["format"] == "gpx"

    async def test_export_route_invalid_format(self, mcp):
        """Test export with invalid format."""
        from fastmcp.exceptions import ToolError

        async with Client(mcp) as client:
            # FastMCP validates parameters before calling the tool,
            # so invalid format raises ToolError
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool("export_route", {"route_id": 987654, "format": "invalid"})

            assert "validation error" in str(exc_info.value).lower()
            assert "invalid" in str(exc_info.value)

    async def test_export_route_not_found(self, stub_api, mcp):
        """Test exporting non-existent route."""
        stub_api.stub_error_response("/routes/999999/export_gpx", status_code=404)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": 999999, "format": "gpx"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]

    async def test_export_route_rate_limit(self, stub_api, mcp):
        """Test exporting route with rate limit error."""
        stub_api.stub_error_response("/routes/987654/export_gpx", status_code=429)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": 987654, "format": "gpx"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]

    async def test_export_route_size_bytes(self, stub_api, mcp):
        """Test that size_bytes is calculated correctly."""
        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        async with Client(mcp) as client:
            result = await client.call_tool("export_route", {"route_id": route_id, "format": "gpx"})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        expected_size = len(GPX_DATA.encode("utf-8"))
        assert data["data"]["size_bytes"] == expected_size


class TestRoutePagination:
    """Test pagination behavior for route tools."""

    async def test_query_routes_pagination_has_more(self, stub_api, respx_mock, mcp):
        """Test routes pagination with more pages available."""
        from httpx import Response

        # Stub athlete endpoint
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        # Create 11 routes (limit+1 to trigger has_more)
        routes = [{**ROUTE, "id": 7000 + i, "name": f"Route {i}"} for i in range(11)]

        def routes_response(request):
            return Response(200, json=routes)

        athlete_id = DETAILED_ATHLETE["id"]
        respx_mock.get(f"/athletes/{athlete_id}/routes").mock(side_effect=routes_response)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "pagination" in data
        assert data["pagination"]["has_more"] is True
        assert data["pagination"]["cursor"] is not None
        assert data["pagination"]["limit"] == 10
        assert len(data["data"]["routes"]) == 10

    async def test_query_routes_pagination_last_page(self, stub_api, respx_mock, mcp):
        """Test routes pagination on last page."""
        from httpx import Response

        # Stub athlete endpoint
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        # Create only 5 routes (less than limit)
        routes = [{**ROUTE, "id": 8000 + i, "name": f"Route {i}"} for i in range(5)]

        def routes_response(request):
            return Response(200, json=routes)

        athlete_id = DETAILED_ATHLETE["id"]
        respx_mock.get(f"/athletes/{athlete_id}/routes").mock(side_effect=routes_response)

        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "pagination" in data
        assert data["pagination"]["has_more"] is False
        assert data["pagination"]["cursor"] is None
        assert data["pagination"]["returned"] == 5

    async def test_query_routes_pagination_with_cursor(self, stub_api, respx_mock, mcp):
        """Test routes pagination using cursor."""
        from httpx import Response

        from strava_mcp.pagination import encode_cursor

        # Stub athlete endpoint
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        # Create routes for page 2
        routes_page2 = [{**ROUTE, "id": 9000 + i, "name": f"Route Page2 {i}"} for i in range(8)]

        def routes_response(request):
            # Verify page parameter is 2
            assert request.url.params.get("page") == "2"
            return Response(200, json=routes_page2)

        athlete_id = DETAILED_ATHLETE["id"]
        respx_mock.get(f"/athletes/{athlete_id}/routes").mock(side_effect=routes_response)

        cursor = encode_cursor(2)
        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"cursor": cursor, "limit": 10})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Debug: print response if error
        if "error" in data:
            print(f"ERROR: {data}")

        assert "pagination" in data, f"Response: {data}"
        assert data["pagination"]["returned"] == 8
        assert data["pagination"]["has_more"] is False

    async def test_query_routes_limit_validation(self, mcp):
        """Test route limit validation."""
        # Test limit too high
        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"limit": 100})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "limit" in data["error"]["message"].lower()

        # Test limit too low
        async with Client(mcp) as client:
            result = await client.call_tool("query_routes", {"limit": 0})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
