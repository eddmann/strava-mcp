"""Tests for MCP server resources and prompts."""

import json
from unittest.mock import patch

import pytest

from strava_mcp import server
from tests.fixtures.activity_fixtures import DETAILED_ACTIVITY, SUMMARY_ACTIVITY
from tests.fixtures.athlete_fixtures import ATHLETE_STATS, ATHLETE_ZONES, DETAILED_ATHLETE
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestMCPResources:
    """Test MCP resources."""

    @patch("strava_mcp.tools.athlete.load_config")
    @patch("strava_mcp.tools.athlete.validate_credentials")
    async def test_athlete_profile_resource(
        self, mock_validate, mock_load_config, mock_config, stub_api
    ):
        """Test athlete profile resource."""
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True

        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        # Call the resource function
        result = await server.athlete_profile_resource()
        data = json.loads(result)

        # Verify structure
        assert "data" in data
        assert "metadata" in data

        # Should have profile, zones, AND stats (complete context)
        assert "profile" in data["data"]
        assert "zones" in data["data"]
        assert "statistics" in data["data"]

        # Verify profile data
        profile = data["data"]["profile"]
        assert profile["id"] == athlete_id
        assert profile["name"] == "Marianne Teutenberg"

        # Verify zones data
        zones = data["data"]["zones"]
        assert "heart_rate" in zones

        # Verify stats data (should have recent stats)
        stats = data["data"]["statistics"]
        assert "recent" in stats


class TestMCPPrompts:
    """Test MCP prompts."""

    async def test_analyze_recent_training_prompt(self):
        """Test analyze_recent_training prompt."""
        result = await server.analyze_recent_training(period="30d")

        # Verify it returns a string with instructions
        assert isinstance(result, str)
        assert "30d" in result
        assert "analyze_training" in result
        assert "volume" in result.lower()
        assert "distribution" in result.lower()

    async def test_analyze_recent_training_prompt_default(self):
        """Test analyze_recent_training prompt with default period."""
        result = await server.analyze_recent_training()

        # Should use default 30d
        assert isinstance(result, str)
        assert "30d" in result

    async def test_segment_performance_prompt(self):
        """Test segment_performance prompt."""
        segment_id = 12345
        result = await server.segment_performance(segment_id=segment_id)

        # Verify it returns a string with instructions
        assert isinstance(result, str)
        assert str(segment_id) in result
        assert "query_segments" in result
        assert "get_segment_leaderboard" in result
        assert "performance" in result.lower()

    async def test_activity_deep_dive_prompt(self):
        """Test activity_deep_dive prompt."""
        activity_id = 98765
        result = await server.activity_deep_dive(activity_id=activity_id)

        # Verify it returns a string with instructions
        assert isinstance(result, str)
        assert str(activity_id) in result
        assert "query_activities" in result
        assert "include_laps" in result
        assert "include_zones" in result
        assert "find_similar_activities" in result

    async def test_compare_recent_runs_prompt(self):
        """Test compare_recent_runs prompt."""
        result = await server.compare_recent_runs()

        # Verify it returns a string with instructions
        assert isinstance(result, str)
        assert "query_activities" in result
        assert "compare_activities" in result
        assert "Run" in result
        assert "improvements" in result.lower()

    async def test_training_summary_prompt(self):
        """Test training_summary prompt."""
        result = await server.training_summary()

        # Verify it returns a string with instructions
        assert isinstance(result, str)
        assert "analyze_training" in result
        assert "30d" in result
        assert "90 days" in result
        assert "comprehensive" in result.lower()
