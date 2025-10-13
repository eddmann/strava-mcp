"""Comprehensive tests for route tools."""

import json
from unittest.mock import patch

import pytest

from strava_mcp.tools.routes import export_route, query_routes
from tests.fixtures.athlete_fixtures import DETAILED_ATHLETE
from tests.fixtures.route_fixtures import GPX_DATA, ROUTE, ROUTE_LIST, TCX_DATA
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestQueryRoutes:
    """Test query_routes tool."""

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_single_route(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying single route by ID."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)

        result = await query_routes(route_id=route_id)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_with_segments(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying route with segments."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

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

        result = await query_routes(route_id=route_id)
        data = json.loads(result)

        # Debug: print result if there's an error
        if "error" in data:
            print(f"Error in response: {data['error']}")

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

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_list(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test listing all routes."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        result = await query_routes(list_all=True)
        data = json.loads(result)

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

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_default_list(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test that default query lists routes."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        result = await query_routes()
        data = json.loads(result)

        assert data["metadata"]["query_type"] == "list_routes"
        assert "routes" in data["data"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_with_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying routes with custom limit."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        routes = [ROUTE_LIST[0] for _ in range(50)]
        stub_api.stub_routes_endpoint(athlete_id, routes)

        result = await query_routes(list_all=True, limit=10)
        data = json.loads(result)

        # Should return max 10 routes
        assert len(data["data"]["routes"]) <= 10

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_with_feet_units(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying routes with feet/miles units."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)

        result = await query_routes(route_id=route_id, unit="feet")
        data = json.loads(result)

        # Check that formatted values use miles/feet
        assert "mi" in data["data"]["route"]["distance"]["formatted"]
        assert "ft" in data["data"]["route"]["elevation_gain"]["formatted"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_empty_list(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying routes with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, [])

        result = await query_routes(list_all=True)
        data = json.loads(result)

        assert data["data"]["count"] == 0
        assert data["data"]["routes"] == []

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying non-existent route."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/routes/999999", status_code=404)

        result = await query_routes(route_id=999999)
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test querying routes when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await query_routes()
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_query_routes_rate_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test querying routes with rate limit error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/routes/987654", status_code=429)

        result = await query_routes(route_id=987654)
        data = json.loads(result)

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]


class TestExportRoute:
    """Test export_route tool."""

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_gpx(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful GPX export."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route(route_id, format="gpx")
        data = json.loads(result)

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

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_tcx(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful TCX export."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_export_tcx_endpoint(route_id, TCX_DATA)

        result = await export_route(route_id, format="tcx")
        data = json.loads(result)

        # Check structure
        assert data["data"]["route_id"] == route_id
        assert data["data"]["format"] == "tcx"
        assert data["data"]["content"] == TCX_DATA
        assert data["data"]["filename"] == f"route_{route_id}.tcx"

        # Check metadata
        assert data["metadata"]["export_format"] == "tcx"

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_default_gpx(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test that default format is GPX."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route(route_id)
        data = json.loads(result)

        assert data["data"]["format"] == "gpx"

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_invalid_format(self, mock_validate, mock_load_config, mock_config):
        """Test export with invalid format."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        result = await export_route(987654, format="invalid")
        data = json.loads(result)

        assert "error" in data
        assert "validation_error" in data["error"]["type"]
        assert "invalid" in data["error"]["message"].lower()

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_not_found(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test exporting non-existent route."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/routes/999999/export_gpx", status_code=404)

        result = await export_route(999999, format="gpx")
        data = json.loads(result)

        assert "error" in data
        assert "not_found" in data["error"]["type"]
        assert "suggestions" in data["error"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test exporting route when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await export_route(987654)
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_rate_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test exporting route with rate limit error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/routes/987654/export_gpx", status_code=429)

        result = await export_route(987654, format="gpx")
        data = json.loads(result)

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]

    @patch("strava_mcp.tools.routes.load_config")
    @patch("strava_mcp.tools.routes.validate_credentials")
    async def test_export_route_size_bytes(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test that size_bytes is calculated correctly."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route(route_id, format="gpx")
        data = json.loads(result)

        expected_size = len(GPX_DATA.encode("utf-8"))
        assert data["data"]["size_bytes"] == expected_size
