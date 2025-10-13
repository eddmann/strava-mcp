"""Comprehensive tests for athlete tools."""

import json
from unittest.mock import patch

import pytest

from strava_mcp.tools.athlete import get_athlete_profile
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

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_full(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting full profile with stats and zones."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)

        result = await get_athlete_profile()
        data = json.loads(result)

        # Check structure
        assert "data" in data
        assert "profile" in data["data"]
        assert "statistics" in data["data"]
        assert "zones" in data["data"]

        # Check profile
        profile = data["data"]["profile"]
        assert profile["id"] == athlete_id
        assert profile["name"] == "Marianne Teutenberg"
        assert profile["username"] == "marianne_t"
        assert profile["location"]["city"] == "San Francisco"
        assert profile["location"]["state"] == "CA"
        assert profile["location"]["country"] == "US"
        assert profile["measurement_preference"] == "feet"

        # Check statistics (default is "all")
        stats = data["data"]["statistics"]
        assert "recent" in stats
        assert "ytd" in stats
        assert "all_time" in stats

        # Check recent stats
        assert stats["recent"]["description"] == "Last 4 weeks"
        assert "run" in stats["recent"]
        assert "ride" in stats["recent"]
        assert "swim" in stats["recent"]

        # Check structured metrics
        assert "meters" in stats["recent"]["run"]["distance"]
        assert "formatted" in stats["recent"]["run"]["distance"]
        assert "seconds" in stats["recent"]["run"]["moving_time"]
        assert "formatted" in stats["recent"]["run"]["moving_time"]

        # Check zones
        zones = data["data"]["zones"]
        assert "heart_rate" in zones
        assert "power" in zones

        # Check metadata
        assert "metadata" in data
        assert "includes" in data["metadata"]
        assert "stats:all" in data["metadata"]["includes"]
        assert "zones" in data["metadata"]["includes"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_profile_only(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting profile without stats or zones."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        result = await get_athlete_profile(include_stats=False, include_zones=False)
        data = json.loads(result)

        # Should have profile but not stats or zones
        assert "profile" in data["data"]
        assert "statistics" not in data["data"]
        assert "zones" not in data["data"]

        # Metadata should show no includes
        assert data["metadata"]["includes"] == []

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_recent_stats(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting profile with recent stats only."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        result = await get_athlete_profile(
            include_stats=True, include_zones=False, stats_period="recent"
        )
        data = json.loads(result)

        # Should have recent stats only
        stats = data["data"]["statistics"]
        assert "recent" in stats
        assert "ytd" not in stats
        assert "all_time" not in stats

        # Metadata should show recent period
        assert "stats:recent" in data["metadata"]["includes"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_ytd_stats(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting profile with YTD stats only."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        result = await get_athlete_profile(
            include_stats=True, include_zones=False, stats_period="ytd"
        )
        data = json.loads(result)

        # Should have YTD stats only
        stats = data["data"]["statistics"]
        assert "recent" not in stats
        assert "ytd" in stats
        assert "all_time" not in stats

        # Metadata should show ytd period
        assert "stats:ytd" in data["metadata"]["includes"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_with_ftp_and_weight(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with FTP and weight values."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_with_ftp = {**DETAILED_ATHLETE, "ftp": 250, "weight": 75.0}
        stub_api.stub_athlete_endpoint(athlete_with_ftp)

        result = await get_athlete_profile(include_stats=False, include_zones=False)
        data = json.loads(result)

        profile = data["data"]["profile"]
        assert "ftp" in profile
        assert profile["ftp"]["watts"] == 250
        assert "weight" in profile
        assert profile["weight"]["kg"] == 75.0
        assert "formatted" in profile["weight"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_with_bikes_and_shoes(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with bikes and shoes."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_with_gear = {
            **DETAILED_ATHLETE,
            "bikes": [
                {
                    "id": "b123",
                    "name": "Trek Domane",
                    "primary": True,
                    "distance": 1000000,
                    "resource_state": 2,
                }
            ],
            "shoes": [
                {
                    "id": "s456",
                    "name": "Nike Pegasus",
                    "primary": True,
                    "distance": 500000,
                    "resource_state": 2,
                }
            ],
        }
        stub_api.stub_athlete_endpoint(athlete_with_gear)

        result = await get_athlete_profile(include_stats=False, include_zones=False)
        data = json.loads(result)

        profile = data["data"]["profile"]
        assert "bikes" in profile
        assert len(profile["bikes"]) == 1
        assert profile["bikes"][0]["name"] == "Trek Domane"
        assert profile["bikes"][0]["primary"] is True
        assert "distance" in profile["bikes"][0]
        assert "meters" in profile["bikes"][0]["distance"]
        assert "formatted" in profile["bikes"][0]["distance"]

        assert "shoes" in profile
        assert len(profile["shoes"]) == 1
        assert profile["shoes"][0]["name"] == "Nike Pegasus"

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_zones_only(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test getting profile with zones only."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)

        result = await get_athlete_profile(include_stats=False, include_zones=True)
        data = json.loads(result)

        assert "profile" in data["data"]
        assert "statistics" not in data["data"]
        assert "zones" in data["data"]

        zones = data["data"]["zones"]
        assert "heart_rate" in zones
        assert "power" in zones

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_hr_zones_only(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with only heart rate zones."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES_HR_ONLY)

        result = await get_athlete_profile(include_stats=False, include_zones=True)
        data = json.loads(result)

        zones = data["data"]["zones"]
        assert "heart_rate" in zones
        assert "power" not in zones

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_with_feet_units(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with feet/miles units."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        athlete_with_gear = {
            **DETAILED_ATHLETE,
            "bikes": [
                {
                    "id": "b123",
                    "name": "Trek",
                    "primary": True,
                    "distance": 10000,
                    "resource_state": 2,
                }
            ],
        }
        stub_api.stub_athlete_endpoint(athlete_with_gear)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        result = await get_athlete_profile(
            include_stats=True, include_zones=False, stats_period="recent", unit="feet"
        )
        data = json.loads(result)

        # Check that formatted values use miles/feet
        stats = data["data"]["statistics"]
        assert "mi" in stats["recent"]["run"]["distance"]["formatted"]
        assert "ft" in stats["recent"]["run"]["elevation_gain"]["formatted"]

        # Check bike distance uses miles
        assert "mi" in data["data"]["profile"]["bikes"][0]["distance"]["formatted"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_not_authenticated(
        self, mock_validate, mock_load_config, mock_config
    ):
        """Test profile when not authenticated."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = False

        result = await get_athlete_profile()
        data = json.loads(result)

        assert "error" in data
        assert "authentication_required" in data["error"]["type"]
        assert "suggestions" in data["error"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_api_error(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with API error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/athlete", status_code=500)

        result = await get_athlete_profile()
        data = json.loads(result)

        assert "error" in data
        assert "api_error" in data["error"]["type"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_rate_limit(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with rate limit error."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        stub_api.stub_error_response("/athlete", status_code=429)

        result = await get_athlete_profile()
        data = json.loads(result)

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]
        assert "suggestions" in data["error"]

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_get_athlete_profile_minimal_fields(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test profile with minimal athlete data."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        minimal_athlete = {
            "id": 123,
            "firstname": "John",
            "lastname": "Doe",
            "resource_state": 2,
        }
        stub_api.stub_athlete_endpoint(minimal_athlete)

        result = await get_athlete_profile(include_stats=False, include_zones=False)
        data = json.loads(result)

        profile = data["data"]["profile"]
        assert profile["id"] == 123
        assert profile["name"] == "John Doe"
        # Optional fields should not be present if missing
        assert "weight" not in profile
        assert "ftp" not in profile
