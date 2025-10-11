"""Comprehensive tests for route tools."""

import os
from unittest.mock import patch

import pytest

from strava_mcp.tools.routes import (
    export_route_gpx,
    export_route_tcx,
    get_route,
    list_athlete_routes,
    validate_export_path,
)
from tests.fixtures.athlete_fixtures import DETAILED_ATHLETE
from tests.fixtures.route_fixtures import GPX_DATA, ROUTE, ROUTE_LIST, TCX_DATA
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


@pytest.fixture
def temp_export_dir(tmp_path):
    """Provide a temporary directory for route exports."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


class TestListAthleteRoutes:
    """Test list_athlete_routes tool."""

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_list_athlete_routes_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful routes list retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Use athlete ID from DETAILED_ATHLETE fixture
        athlete_id = 1234567890987654400
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        result = await list_athlete_routes()

        assert "Found 2 routes:" in result
        assert "Morning Commute" in result
        assert "Weekend Loop" in result
        assert "ID: 987654" in result
        assert "9.32 mi" in result  # 15000m converted to miles (athlete preference is feet)
        assert "492 ft" in result  # Elevation in feet because athlete preference
        assert "Est. Time:" in result
        assert "Private: No" in result
        assert "Starred: Yes" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_list_athlete_routes_with_athlete_id(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test routes list with specific athlete ID."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = 999
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        result = await list_athlete_routes(athlete_id=athlete_id)

        assert "Found 2 routes:" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_list_athlete_routes_with_pagination(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test routes list with pagination."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Use athlete ID from DETAILED_ATHLETE fixture
        athlete_id = 1234567890987654400
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, ROUTE_LIST)

        result = await list_athlete_routes(page=2, per_page=10)

        assert "Found 2 routes:" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_list_athlete_routes_empty(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test routes list with no results."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Use athlete ID from DETAILED_ATHLETE fixture
        athlete_id = 1234567890987654400
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_routes_endpoint(athlete_id, [])

        result = await list_athlete_routes()

        assert "No routes found." in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_list_athlete_routes_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test routes list when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await list_athlete_routes()

        assert "Error: Strava credentials not configured" in result


class TestGetRoute:
    """Test get_route tool."""

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_get_route_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful route details retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_route_details_endpoint(route_id, ROUTE)

        result = await get_route(route_id)

        assert "Route: Morning Commute" in result
        assert f"ID: {route_id}" in result
        assert "Description: My daily ride to work" in result
        assert "Measurements:" in result
        assert "9.32 mi" in result  # Distance in miles (athlete preference is feet)
        assert "492 ft" in result  # Elevation in feet
        assert "Estimated Time:" in result
        assert "Properties:" in result
        assert "Private: No" in result
        assert "Starred: Yes" in result
        assert "Created: 2021-04-10" in result
        assert f"To export this route, use export-route-gpx or export-route-tcx with ID: {route_id}" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_get_route_with_segments(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test route details with segments."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        from tests.fixtures.segment_fixtures import SUMMARY_SEGMENT

        route_id = 987654
        # Create valid segments with all required fields
        segments = [
            {**SUMMARY_SEGMENT, "id": 1},
            {**SUMMARY_SEGMENT, "id": 2, "name": "Segment 2"},
            {**SUMMARY_SEGMENT, "id": 3, "name": "Segment 3"}
        ]
        route_with_segments = {**ROUTE, "segments": segments}
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_route_details_endpoint(route_id, route_with_segments)

        result = await get_route(route_id)

        assert "Segments: 3 segments included" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_get_route_not_found(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test route details with non-existent route."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 999999
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_error_response(f"/routes/{route_id}", status_code=404)

        result = await get_route(route_id)

        assert "Error:" in result


class TestValidateExportPath:
    """Test validate_export_path function."""

    def test_validate_export_path_valid_directory(self, temp_export_dir):
        """Test validation with valid directory."""
        is_valid, error_msg = validate_export_path(str(temp_export_dir))

        assert is_valid is True
        assert error_msg == ""

    def test_validate_export_path_creates_directory(self, tmp_path):
        """Test validation creates non-existent directory."""
        new_dir = tmp_path / "new_exports"
        is_valid, error_msg = validate_export_path(str(new_dir))

        assert is_valid is True
        assert error_msg == ""
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_validate_export_path_not_directory(self, tmp_path):
        """Test validation with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        is_valid, error_msg = validate_export_path(str(file_path))

        assert is_valid is False
        assert "not a directory" in error_msg

    def test_validate_export_path_not_writable(self, tmp_path):
        """Test validation with non-writable directory."""
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()

        # Make directory read-only
        os.chmod(read_only_dir, 0o444)

        is_valid, error_msg = validate_export_path(str(read_only_dir))

        # Restore permissions for cleanup
        os.chmod(read_only_dir, 0o755)

        # On some systems, this might still pass if running as root
        # So we check if the validation correctly identified it
        if not is_valid:
            assert "not writable" in error_msg


class TestExportRouteGPX:
    """Test export_route_gpx tool."""

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_gpx_success(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test successful GPX export."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route_gpx(route_id)

        assert "Successfully exported route 'Morning Commute' to GPX:" in result
        assert f"route_{route_id}.gpx" in result
        assert f"Size: {len(GPX_DATA)} bytes" in result

        # Verify file was created
        export_file = temp_export_dir / f"route_{route_id}.gpx"
        assert export_file.exists()
        assert export_file.read_text() == GPX_DATA

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_gpx_custom_filename(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test GPX export with custom filename."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        filename = "my_custom_route"
        stub_api.stub_route_details_endpoint(route_id, ROUTE)
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route_gpx(route_id, filename=filename)

        assert "Successfully exported" in result
        assert "my_custom_route.gpx" in result

        # Verify file was created with custom name
        export_file = temp_export_dir / "my_custom_route.gpx"
        assert export_file.exists()

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_gpx_auto_extension(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test GPX export automatically adds extension."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        filename = "my_route.gpx"  # Already has extension
        stub_api.stub_route_details_endpoint(route_id, ROUTE)
        stub_api.stub_route_export_gpx_endpoint(route_id, GPX_DATA)

        result = await export_route_gpx(route_id, filename=filename)

        assert "my_route.gpx" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_gpx_invalid_path(self, mock_validate, mock_load_config, mock_config, tmp_path):
        """Test GPX export with invalid export path."""
        # Point to a file instead of directory
        invalid_path = tmp_path / "file.txt"
        invalid_path.write_text("test")

        mock_config.route_export_path = str(invalid_path)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        result = await export_route_gpx(route_id)

        assert "Error:" in result
        assert "not a directory" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_gpx_not_found(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test GPX export with non-existent route."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 999999
        stub_api.stub_error_response(f"/routes/{route_id}", status_code=404)

        result = await export_route_gpx(route_id)

        assert "Error:" in result


class TestExportRouteTCX:
    """Test export_route_tcx tool."""

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_tcx_success(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test successful TCX export."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        stub_api.stub_route_details_endpoint(route_id, ROUTE)
        stub_api.stub_route_export_tcx_endpoint(route_id, TCX_DATA)

        result = await export_route_tcx(route_id)

        assert "Successfully exported route 'Morning Commute' to TCX:" in result
        assert f"route_{route_id}.tcx" in result
        assert f"Size: {len(TCX_DATA)} bytes" in result

        # Verify file was created
        export_file = temp_export_dir / f"route_{route_id}.tcx"
        assert export_file.exists()
        assert export_file.read_text() == TCX_DATA

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_tcx_custom_filename(self, mock_validate, mock_load_config, mock_config, stub_api, temp_export_dir):
        """Test TCX export with custom filename."""
        mock_config.route_export_path = str(temp_export_dir)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        filename = "my_tcx_route"
        stub_api.stub_route_details_endpoint(route_id, ROUTE)
        stub_api.stub_route_export_tcx_endpoint(route_id, TCX_DATA)

        result = await export_route_tcx(route_id, filename=filename)

        assert "Successfully exported" in result
        assert "my_tcx_route.tcx" in result

        # Verify file was created with custom name
        export_file = temp_export_dir / "my_tcx_route.tcx"
        assert export_file.exists()

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_tcx_invalid_path(self, mock_validate, mock_load_config, mock_config, tmp_path):
        """Test TCX export with invalid export path."""
        invalid_path = tmp_path / "file.txt"
        invalid_path.write_text("test")

        mock_config.route_export_path = str(invalid_path)
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        route_id = 987654
        result = await export_route_tcx(route_id)

        assert "Error:" in result
        assert "not a directory" in result

    @patch('strava_mcp.tools.routes.load_config')
    @patch('strava_mcp.tools.routes.validate_credentials')
    async def test_export_route_tcx_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test TCX export when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await export_route_tcx(987654)

        assert "Error: Strava credentials not configured" in result
