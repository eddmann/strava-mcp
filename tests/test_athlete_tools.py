"""Comprehensive tests for athlete tools."""

from unittest.mock import patch

import pytest

from strava_mcp.tools.athlete import get_athlete_profile, get_athlete_stats, get_athlete_zones
from tests.fixtures.athlete_fixtures import (
    ATHLETE_STATS,
    ATHLETE_ZONES,
    ATHLETE_ZONES_HR_ONLY,
    DETAILED_ATHLETE,
)
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestGetAthleteProfile:
    """Test get_athlete_profile tool."""

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_profile_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful athlete profile retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        result = await get_athlete_profile()

        assert "Athlete Profile: Marianne Teutenberg" in result
        assert "ID: 1234567890987654400" in result
        assert "Username: marianne_t" in result
        assert "City: San Francisco" in result
        assert "State: CA" in result
        assert "Country: US" in result
        assert "Premium: Yes" in result
        assert "Summit: Yes" in result
        assert "Measurement: feet" in result
        # Weight is 0 in fixture which is falsy, so won't be displayed
        # FTP is None in fixture, so it should not appear

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_profile_with_ftp(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete profile with FTP value."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_with_ftp = {**DETAILED_ATHLETE, "ftp": 250, "weight": 75.0}
        stub_api.stub_athlete_endpoint(athlete_with_ftp)

        result = await get_athlete_profile()

        assert "FTP: 250 W" in result
        assert "Weight: 75.0 kg" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_profile_missing_optional_fields(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete profile with minimal fields."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        minimal_athlete = {
            "id": 123,
            "firstname": "John",
            "lastname": "Doe",
            "resource_state": 2
        }
        stub_api.stub_athlete_endpoint(minimal_athlete)

        result = await get_athlete_profile()

        assert "Athlete Profile: John Doe" in result
        assert "ID: 123" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_profile_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test athlete profile when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_athlete_profile()

        assert "Error: Strava credentials not configured" in result
        assert "strava-mcp-auth" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_profile_api_error(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete profile with API error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/athlete", status_code=404, message="Athlete not found")

        result = await get_athlete_profile()

        assert "Error:" in result


class TestGetAthleteStats:
    """Test get_athlete_stats tool."""

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_stats_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful athlete stats retrieval."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = 123456
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        result = await get_athlete_stats(athlete_id)

        # Check header
        assert f"Athlete Stats (ID: {athlete_id})" in result

        # Check recent stats
        assert "=== RECENT (Last 4 Weeks) ===" in result
        assert "Count: 5" in result
        assert "50.00 km" in result  # distance

        # Check YTD stats
        assert "=== YEAR TO DATE ===" in result
        assert "Count: 50" in result

        # Check all-time stats
        assert "=== ALL TIME ===" in result
        assert "Count: 500" in result

        # Check personal bests
        assert "Biggest Ride: 150.00 km" in result
        assert "Biggest Climb: 2000 m" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_stats_default_athlete(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete stats with no athlete_id (defaults to current user)."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        # Mock getting current athlete first
        current_athlete = {**DETAILED_ATHLETE, "id": 999}
        stub_api.stub_athlete_endpoint(current_athlete)
        stub_api.stub_athlete_stats_endpoint(999, ATHLETE_STATS)

        result = await get_athlete_stats()

        assert "Athlete Stats (ID: 999)" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_stats_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test athlete stats when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_athlete_stats(123)

        assert "Error: Strava credentials not configured" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_stats_api_error(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete stats with API error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = 123456
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_error_response(f"/athletes/{athlete_id}/stats", status_code=404)

        result = await get_athlete_stats(athlete_id)

        assert "Error:" in result


class TestGetAthleteZones:
    """Test get_athlete_zones tool."""

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_zones_success(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test successful athlete zones retrieval with both HR and power."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)

        result = await get_athlete_zones()

        # Check heart rate zones
        assert "=== HEART RATE ZONES ===" in result
        assert "Custom Zones: No" in result
        assert "Zone 1: 0 - 140 bpm" in result
        assert "Zone 5: 190 - -1 bpm" in result

        # Check power zones
        assert "=== POWER ZONES ===" in result
        assert "Zone 1: 0 - 150 W" in result
        assert "Zone 5: 300 - -1 W" in result

        # Check raw JSON is included
        assert "--- Raw Zone Data (JSON) ---" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_zones_hr_only(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete zones with only heart rate zones."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES_HR_ONLY)

        result = await get_athlete_zones()

        # Check heart rate zones exist
        assert "=== HEART RATE ZONES ===" in result
        assert "Custom Zones: Yes" in result

        # Power zones should not be present
        assert "=== POWER ZONES ===" not in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_zones_none(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete zones when no zones are configured."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        empty_zones = {"heart_rate": None, "power": None}
        stub_api.stub_athlete_zones_endpoint(empty_zones)

        result = await get_athlete_zones()

        assert "No training zones configured for this athlete." in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_zones_not_authenticated(self, mock_validate, mock_load_config, mock_config):
        """Test athlete zones when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_athlete_zones()

        assert "Error: Strava credentials not configured" in result

    @patch('strava_mcp.tools.athlete.load_config')
    @patch('strava_mcp.tools.athlete.validate_credentials')
    async def test_get_athlete_zones_forbidden(self, mock_validate, mock_load_config, mock_config, stub_api):
        """Test athlete zones with 403 forbidden (insufficient scope)."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/athlete/zones", status_code=403, message="Forbidden")

        result = await get_athlete_zones()

        assert "Error: Access denied" in result
        assert "profile:read_all" in result
        assert "strava-mcp-auth" in result
