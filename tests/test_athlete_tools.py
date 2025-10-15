"""Comprehensive tests for athlete tools."""

import json

import pytest
from fastmcp import Client

from strava_mcp.server import mcp
from tests.fixtures.athlete_fixtures import (
    ATHLETE_STATS,
    ATHLETE_ZONES,
    ATHLETE_ZONES_HR_ONLY,
    DETAILED_ATHLETE,
)
from tests.helpers import get_text_content
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestGetAthleteProfile:
    """Test get_athlete_profile tool."""

    async def test_get_athlete_profile_full(self, stub_api):
        """Test getting full profile with stats and zones."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)

        async with Client(mcp) as client:
            result = await client.call_tool("get_athlete_profile", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_get_athlete_profile_profile_only(self, stub_api):
        """Test getting profile without stats or zones."""
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": False}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should have profile but not stats or zones
        assert "profile" in data["data"]
        assert "statistics" not in data["data"]
        assert "zones" not in data["data"]

        # Metadata should show no includes
        assert data["metadata"]["includes"] == []

    async def test_get_athlete_profile_recent_stats(self, stub_api):
        """Test getting profile with recent stats only."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile",
                {"include_stats": True, "include_zones": False, "stats_period": "recent"},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should have recent stats only
        stats = data["data"]["statistics"]
        assert "recent" in stats
        assert "ytd" not in stats
        assert "all_time" not in stats

        # Metadata should show recent period
        assert "stats:recent" in data["metadata"]["includes"]

    async def test_get_athlete_profile_ytd_stats(self, stub_api):
        """Test getting profile with YTD stats only."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile",
                {"include_stats": True, "include_zones": False, "stats_period": "ytd"},
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Should have YTD stats only
        stats = data["data"]["statistics"]
        assert "recent" not in stats
        assert "ytd" in stats
        assert "all_time" not in stats

        # Metadata should show ytd period
        assert "stats:ytd" in data["metadata"]["includes"]

    async def test_get_athlete_profile_with_ftp_and_weight(self, stub_api):
        """Test profile with FTP and weight values."""
        athlete_with_ftp = {**DETAILED_ATHLETE, "ftp": 250, "weight": 75.0}
        stub_api.stub_athlete_endpoint(athlete_with_ftp)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": False}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        profile = data["data"]["profile"]
        assert "ftp" in profile
        assert profile["ftp"]["watts"] == 250
        assert "weight" in profile
        assert profile["weight"]["kg"] == 75.0
        assert "formatted" in profile["weight"]

    async def test_get_athlete_profile_with_bikes_and_shoes(self, stub_api):
        """Test profile with bikes and shoes."""
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

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": False}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

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

    async def test_get_athlete_profile_zones_only(self, stub_api):
        """Test getting profile with zones only."""
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "profile" in data["data"]
        assert "statistics" not in data["data"]
        assert "zones" in data["data"]

        zones = data["data"]["zones"]
        assert "heart_rate" in zones
        assert "power" in zones

    async def test_get_athlete_profile_hr_zones_only(self, stub_api):
        """Test profile with only heart rate zones."""
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES_HR_ONLY)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": True}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        zones = data["data"]["zones"]
        assert "heart_rate" in zones
        assert "power" not in zones

    async def test_get_athlete_profile_with_feet_units(self, stub_api):
        """Test profile with feet/miles units."""
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

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile",
                {
                    "include_stats": True,
                    "include_zones": False,
                    "stats_period": "recent",
                    "unit": "feet",
                },
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        # Check that formatted values use miles/feet
        stats = data["data"]["statistics"]
        assert "mi" in stats["recent"]["run"]["distance"]["formatted"]
        assert "ft" in stats["recent"]["run"]["elevation_gain"]["formatted"]

        # Check bike distance uses miles
        assert "mi" in data["data"]["profile"]["bikes"][0]["distance"]["formatted"]

    async def test_get_athlete_profile_api_error(self, stub_api):
        """Test profile with API error."""
        stub_api.stub_error_response("/athlete", status_code=500)

        async with Client(mcp) as client:
            result = await client.call_tool("get_athlete_profile", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "api_error" in data["error"]["type"]

    async def test_get_athlete_profile_rate_limit(self, stub_api):
        """Test profile with rate limit error."""
        stub_api.stub_error_response("/athlete", status_code=429)

        async with Client(mcp) as client:
            result = await client.call_tool("get_athlete_profile", {})

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        assert "error" in data
        assert "rate_limit" in data["error"]["type"]
        assert "suggestions" in data["error"]

    async def test_get_athlete_profile_minimal_fields(self, stub_api):
        """Test profile with minimal athlete data."""
        minimal_athlete = {
            "id": 123,
            "firstname": "John",
            "lastname": "Doe",
            "resource_state": 2,
        }
        stub_api.stub_athlete_endpoint(minimal_athlete)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_athlete_profile", {"include_stats": False, "include_zones": False}
            )

            assert result.is_error is False
            data = json.loads(get_text_content(result))

        profile = data["data"]["profile"]
        assert profile["id"] == 123
        assert profile["name"] == "John Doe"
        # Optional fields should not be present if missing
        assert "weight" not in profile
        assert "ftp" not in profile
