"""Tests for MCP server resources and prompts."""

import json

import pytest
from fastmcp import Client

from tests.fixtures.athlete_fixtures import ATHLETE_STATS, ATHLETE_ZONES, DETAILED_ATHLETE
from tests.helpers import get_prompt_text, get_resource_text
from tests.stubs.strava_api_stub import StravaAPIStubber


@pytest.fixture
def stub_api(respx_mock):
    """Provide a Strava API stubber."""
    return StravaAPIStubber(respx_mock)


class TestMCPResources:
    """Test MCP resources."""

    async def test_athlete_profile_resource(self, stub_api, mcp):
        """Test athlete profile resource."""
        athlete_id = DETAILED_ATHLETE["id"]
        stub_api.stub_athlete_endpoint(DETAILED_ATHLETE)
        stub_api.stub_athlete_zones_endpoint(ATHLETE_ZONES)
        stub_api.stub_athlete_stats_endpoint(athlete_id, ATHLETE_STATS)

        async with Client(mcp) as client:
            # Read the resource
            contents = await client.read_resource("strava://athlete/profile")

            # Verify we got contents
            assert len(contents) > 0
            data = json.loads(get_resource_text(contents[0]))

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

    async def test_analyze_recent_training_prompt(self, mcp):
        """Test analyze_recent_training prompt."""
        async with Client(mcp) as client:
            result = await client.get_prompt("analyze_recent_training", {"period": "30d"})

            # Verify it returns messages
            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert "30d" in prompt_text
        assert "analyze_training" in prompt_text
        assert "volume" in prompt_text.lower()
        assert "distribution" in prompt_text.lower()

    async def test_analyze_recent_training_prompt_default(self, mcp):
        """Test analyze_recent_training prompt with default period."""
        async with Client(mcp) as client:
            result = await client.get_prompt("analyze_recent_training", {})

            # Should use default 30d
            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert "30d" in prompt_text

    async def test_segment_performance_prompt(self, mcp):
        """Test segment_performance prompt."""
        segment_id = 12345

        async with Client(mcp) as client:
            result = await client.get_prompt("segment_performance", {"segment_id": segment_id})

            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert str(segment_id) in prompt_text
        assert "query_segments" in prompt_text
        assert "get_segment_leaderboard" in prompt_text
        assert "performance" in prompt_text.lower()

    async def test_activity_deep_dive_prompt(self, mcp):
        """Test activity_deep_dive prompt."""
        activity_id = 98765

        async with Client(mcp) as client:
            result = await client.get_prompt("activity_deep_dive", {"activity_id": activity_id})

            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert str(activity_id) in prompt_text
        assert "query_activities" in prompt_text
        assert "include_laps" in prompt_text
        assert "include_zones" in prompt_text
        assert "find_similar_activities" in prompt_text

    async def test_compare_recent_runs_prompt(self, mcp):
        """Test compare_recent_runs prompt."""
        async with Client(mcp) as client:
            result = await client.get_prompt("compare_recent_runs", {})

            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert "query_activities" in prompt_text
        assert "compare_activities" in prompt_text
        assert "Run" in prompt_text
        assert "improvements" in prompt_text.lower()

    async def test_training_summary_prompt(self, mcp):
        """Test training_summary prompt."""
        async with Client(mcp) as client:
            result = await client.get_prompt("training_summary", {})

            assert len(result.messages) > 0
            prompt_text = get_prompt_text(result.messages[0])

        assert "analyze_training" in prompt_text
        assert "30d" in prompt_text
        assert "90 days" in prompt_text
        assert "comprehensive" in prompt_text.lower()
