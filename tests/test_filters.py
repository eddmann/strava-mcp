"""Tests for activity filtering utilities."""

from datetime import datetime
from typing import cast

import pytest

from strava_mcp.filters import (
    apply_filters,
    filter_by_distance,
    filter_by_race,
    filter_by_title,
    parse_distance,
)
from strava_mcp.models import ActivityType, MetaAthlete, SummaryActivity


class TestParseDistance:
    """Test distance parsing for various input formats."""

    def test_parse_race_name_5k(self):
        """Test parsing '5k' race distance."""
        min_dist, max_dist = parse_distance("5k")
        assert min_dist == 4500
        assert max_dist == 5500

    def test_parse_race_name_10k(self):
        """Test parsing '10k' race distance."""
        min_dist, max_dist = parse_distance("10k")
        assert min_dist == 9000
        assert max_dist == 11000

    def test_parse_race_name_15k(self):
        """Test parsing '15k' race distance."""
        min_dist, max_dist = parse_distance("15k")
        assert min_dist == 13500
        assert max_dist == 16500

    def test_parse_race_name_half_marathon(self):
        """Test parsing 'half-marathon' race distance."""
        min_dist, max_dist = parse_distance("half-marathon")
        assert min_dist == 20000
        assert max_dist == 22000

    def test_parse_race_name_half_marathon_alternative(self):
        """Test parsing 'half marathon' with space."""
        min_dist, max_dist = parse_distance("half marathon")
        assert min_dist == 20000
        assert max_dist == 22000

    def test_parse_race_name_half_short(self):
        """Test parsing 'half' shorthand."""
        min_dist, max_dist = parse_distance("half")
        assert min_dist == 20000
        assert max_dist == 22000

    def test_parse_race_name_marathon(self):
        """Test parsing 'marathon' race distance."""
        min_dist, max_dist = parse_distance("marathon")
        assert min_dist == 41000
        assert max_dist == 43000

    def test_parse_race_name_ultra(self):
        """Test parsing 'ultra' race distance (open-ended)."""
        min_dist, max_dist = parse_distance("ultra")
        assert min_dist == 43000
        assert max_dist is None  # No upper limit

    def test_parse_race_name_50k(self):
        """Test parsing '50k' race distance."""
        min_dist, max_dist = parse_distance("50k")
        assert min_dist == 45000
        assert max_dist == 55000

    def test_parse_race_name_100k(self):
        """Test parsing '100k' race distance."""
        min_dist, max_dist = parse_distance("100k")
        assert min_dist == 90000
        assert max_dist == 110000

    def test_parse_race_name_case_insensitive(self):
        """Test that race names are case-insensitive."""
        min_dist1, max_dist1 = parse_distance("MARATHON")
        min_dist2, max_dist2 = parse_distance("Marathon")
        min_dist3, max_dist3 = parse_distance("marathon")

        assert min_dist1 == min_dist2 == min_dist3 == 41000
        assert max_dist1 == max_dist2 == max_dist3 == 43000

    def test_parse_numeric_with_buffer(self):
        """Test parsing numeric value with ±10% buffer."""
        min_dist, max_dist = parse_distance("10000")
        assert min_dist == 9000  # 10000 - 10%
        assert max_dist == 11000  # 10000 + 10%

    def test_parse_numeric_with_buffer_small_value(self):
        """Test parsing small numeric value."""
        min_dist, max_dist = parse_distance("5000")
        assert min_dist == 4500
        assert max_dist == 5500

    def test_parse_numeric_with_buffer_large_value(self):
        """Test parsing large numeric value."""
        min_dist, max_dist = parse_distance("42195")  # Marathon in meters
        buffer = int(42195 * 0.1)  # = 4219
        assert min_dist == 42195 - buffer  # 37976
        assert max_dist == 42195 + buffer  # 46414

    def test_parse_range_exact(self):
        """Test parsing exact range format."""
        min_dist, max_dist = parse_distance("10000:15000")
        assert min_dist == 10000
        assert max_dist == 15000

    def test_parse_range_with_spaces(self):
        """Test parsing range with spaces."""
        min_dist, max_dist = parse_distance("5000 : 10000")
        assert min_dist == 5000
        assert max_dist == 10000

    def test_parse_range_open_ended_min(self):
        """Test parsing range with no minimum."""
        min_dist, max_dist = parse_distance(":10000")
        assert min_dist is None
        assert max_dist == 10000

    def test_parse_range_open_ended_max(self):
        """Test parsing range with no maximum."""
        min_dist, max_dist = parse_distance("5000:")
        assert min_dist == 5000
        assert max_dist is None

    def test_parse_invalid_distance_text(self):
        """Test that invalid text raises ValueError."""
        with pytest.raises(ValueError, match="Invalid distance format"):
            parse_distance("invalid")

    def test_parse_invalid_distance_negative(self):
        """Test that negative distance raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            parse_distance("-1000")

    def test_parse_invalid_range_negative_min(self):
        """Test that negative min in range raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            parse_distance("-1000:5000")

    def test_parse_invalid_range_negative_max(self):
        """Test that negative max in range raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            parse_distance("5000:-1000")

    def test_parse_invalid_range_min_greater_than_max(self):
        """Test that min > max raises ValueError."""
        with pytest.raises(ValueError, match="cannot be greater than maximum"):
            parse_distance("10000:5000")

    def test_parse_invalid_range_too_many_colons(self):
        """Test that multiple colons raise ValueError."""
        with pytest.raises(ValueError, match="Invalid range format"):
            parse_distance("1000:5000:10000")

    def test_parse_invalid_range_non_numeric(self):
        """Test that non-numeric range values raise ValueError."""
        with pytest.raises(ValueError, match="Invalid"):
            parse_distance("abc:def")

    # Unit conversion tests

    def test_parse_kilometers_with_buffer(self):
        """Test parsing kilometers with ±10% buffer."""
        min_dist, max_dist = parse_distance("10km")
        assert min_dist == 9000  # 10000m - 10%
        assert max_dist == 11000  # 10000m + 10%

    def test_parse_kilometers_alias_full(self):
        """Test parsing 'kilometers' (full word) with buffer."""
        min_dist, max_dist = parse_distance("5kilometers")
        assert min_dist == 4500
        assert max_dist == 5500

    def test_parse_miles_with_buffer(self):
        """Test parsing miles with ±10% buffer."""
        min_dist, max_dist = parse_distance("5mi")
        # 5 miles = 8046.7 meters
        expected = 8047
        buffer = int(expected * 0.1)
        assert min_dist == expected - buffer
        assert max_dist == expected + buffer

    def test_parse_miles_alias_full(self):
        """Test parsing 'miles' (full word) with buffer."""
        min_dist, max_dist = parse_distance("3miles")
        expected = 4828  # 3 miles = 4828.02 meters
        buffer = int(expected * 0.1)
        assert min_dist == expected - buffer
        assert max_dist == expected + buffer

    def test_parse_meters_explicit(self):
        """Test explicit meters with 'm' suffix."""
        min_dist, max_dist = parse_distance("10000m")
        assert min_dist == 9000
        assert max_dist == 11000

    def test_parse_meters_alias_full(self):
        """Test parsing 'meters' (full word)."""
        min_dist, max_dist = parse_distance("5000meters")
        assert min_dist == 4500
        assert max_dist == 5500

    def test_parse_decimal_kilometers(self):
        """Test parsing decimal kilometers."""
        min_dist, max_dist = parse_distance("5.5km")
        assert min_dist == 4950  # 5500m - 10%
        assert max_dist == 6050  # 5500m + 10%

    def test_parse_decimal_miles(self):
        """Test parsing decimal miles."""
        min_dist, max_dist = parse_distance("3.1mi")
        # 3.1 miles = 4989.454 meters, rounds to 4989
        expected = 4989
        buffer = int(expected * 0.1)
        assert min_dist == expected - buffer
        assert max_dist == expected + buffer

    def test_parse_unit_case_insensitive(self):
        """Test that units are case-insensitive."""
        result1 = parse_distance("10KM")
        result2 = parse_distance("10Km")
        result3 = parse_distance("10km")
        assert result1 == result2 == result3

    def test_parse_unit_with_space(self):
        """Test parsing value with space before unit."""
        min_dist, max_dist = parse_distance("10 km")
        assert min_dist == 9000
        assert max_dist == 11000

    def test_parse_range_kilometers(self):
        """Test parsing range with kilometers."""
        min_dist, max_dist = parse_distance("5km:10km")
        assert min_dist == 5000
        assert max_dist == 10000

    def test_parse_range_miles(self):
        """Test parsing range with miles."""
        min_dist, max_dist = parse_distance("3mi:6mi")
        assert min_dist == 4828  # 3 miles
        assert max_dist == 9656  # 6 miles

    def test_parse_range_meters_explicit(self):
        """Test parsing range with explicit meters."""
        min_dist, max_dist = parse_distance("5000m:10000m")
        assert min_dist == 5000
        assert max_dist == 10000

    def test_parse_range_decimal_kilometers(self):
        """Test parsing range with decimal kilometers."""
        min_dist, max_dist = parse_distance("5.5km:10.5km")
        assert min_dist == 5500
        assert max_dist == 10500

    def test_parse_range_open_ended_max_with_unit(self):
        """Test open-ended maximum range with unit."""
        min_dist, max_dist = parse_distance("5km:")
        assert min_dist == 5000
        assert max_dist is None

    def test_parse_range_open_ended_min_with_unit(self):
        """Test open-ended minimum range with unit."""
        min_dist, max_dist = parse_distance(":10km")
        assert min_dist is None
        assert max_dist == 10000

    def test_parse_backward_compatible_numeric_only(self):
        """Test backward compatibility - numeric without unit defaults to meters."""
        min_dist, max_dist = parse_distance("10000")
        assert min_dist == 9000
        assert max_dist == 11000

    def test_parse_backward_compatible_range_numeric_only(self):
        """Test backward compatibility - range without units defaults to meters."""
        min_dist, max_dist = parse_distance("5000:10000")
        assert min_dist == 5000
        assert max_dist == 10000

    def test_parse_invalid_unit(self):
        """Test that invalid unit raises ValueError."""
        with pytest.raises(ValueError, match="Unknown unit"):
            parse_distance("10xyz")

    def test_parse_negative_with_unit(self):
        """Test that negative values with units raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            parse_distance("-10km")

    def test_parse_race_name_priority_over_unit(self):
        """Test that race names like '5k' are recognized before unit parsing."""
        min_dist, max_dist = parse_distance("5k")
        # Should be race distance with tolerance, not 5 * k (which would error)
        assert min_dist == 4500
        assert max_dist == 5500

    def test_parse_large_decimal_value(self):
        """Test parsing large decimal value with precision."""
        min_dist, max_dist = parse_distance("42.195km")
        # Marathon distance: 42.195km = 42195m
        # Buffer = int(42195 * 0.1) = int(4219.5) = 4219
        assert min_dist == 37976  # 42195 - 4219
        assert max_dist == 46414  # 42195 + 4219


class TestFilterByDistance:
    """Test distance filtering."""

    def create_activity(self, distance: float, name: str = "Test Activity") -> SummaryActivity:
        """Helper to create a minimal activity for testing."""
        return SummaryActivity(
            id=1,
            name=name,
            distance=distance,
            moving_time=3600,
            elapsed_time=3600,
            total_elevation_gain=100.0,
            type=cast(ActivityType, "Run"),
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            start_date_local=datetime(2024, 1, 1, 0, 0, 0),
            timezone="(GMT+00:00) UTC",
            athlete=MetaAthlete(id=123),
        )

    def test_filter_min_distance(self):
        """Test filtering by minimum distance."""
        activities = [
            self.create_activity(5000),
            self.create_activity(10000),
            self.create_activity(15000),
        ]

        filtered = filter_by_distance(activities, min_distance=9000)
        assert len(filtered) == 2
        assert filtered[0].distance == 10000
        assert filtered[1].distance == 15000

    def test_filter_max_distance(self):
        """Test filtering by maximum distance."""
        activities = [
            self.create_activity(5000),
            self.create_activity(10000),
            self.create_activity(15000),
        ]

        filtered = filter_by_distance(activities, max_distance=11000)
        assert len(filtered) == 2
        assert filtered[0].distance == 5000
        assert filtered[1].distance == 10000

    def test_filter_distance_range(self):
        """Test filtering by distance range."""
        activities = [
            self.create_activity(5000),
            self.create_activity(10000),
            self.create_activity(15000),
            self.create_activity(20000),
        ]

        filtered = filter_by_distance(activities, min_distance=9000, max_distance=16000)
        assert len(filtered) == 2
        assert filtered[0].distance == 10000
        assert filtered[1].distance == 15000

    def test_filter_no_limits_returns_all(self):
        """Test that no limits returns all activities."""
        activities = [
            self.create_activity(5000),
            self.create_activity(10000),
        ]

        filtered = filter_by_distance(activities)
        assert len(filtered) == 2

    def test_filter_distance_inclusive(self):
        """Test that distance filtering is inclusive of boundaries."""
        activities = [
            self.create_activity(9000),
            self.create_activity(10000),
            self.create_activity(11000),
        ]

        filtered = filter_by_distance(activities, min_distance=9000, max_distance=11000)
        assert len(filtered) == 3  # All three should be included


class TestFilterByTitle:
    """Test title filtering."""

    def create_activity(self, name: str) -> SummaryActivity:
        """Helper to create activity with specific name."""
        return SummaryActivity(
            id=1,
            name=name,
            distance=5000,
            moving_time=3600,
            elapsed_time=3600,
            total_elevation_gain=100.0,
            type=cast(ActivityType, "Run"),
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            start_date_local=datetime(2024, 1, 1, 0, 0, 0),
            timezone="(GMT+00:00) UTC",
            athlete=MetaAthlete(id=123),
        )

    def test_filter_case_insensitive(self):
        """Test case-insensitive title filtering."""
        activities = [
            self.create_activity("Morning Run"),
            self.create_activity("Evening PARKRUN"),
            self.create_activity("Tempo Run"),
        ]

        filtered = filter_by_title(activities, "parkrun")
        assert len(filtered) == 1
        assert "PARKRUN" in filtered[0].name

    def test_filter_case_sensitive(self):
        """Test case-sensitive title filtering."""
        activities = [
            self.create_activity("Morning Run"),
            self.create_activity("parkrun"),
            self.create_activity("PARKRUN"),
        ]

        filtered = filter_by_title(activities, "parkrun", case_sensitive=True)
        assert len(filtered) == 1
        assert filtered[0].name == "parkrun"

    def test_filter_substring_match(self):
        """Test substring matching."""
        activities = [
            self.create_activity("Easy Morning Run"),
            self.create_activity("Tempo Run"),
            self.create_activity("Long Run"),
        ]

        filtered = filter_by_title(activities, "Morning")
        assert len(filtered) == 1
        assert filtered[0].name == "Easy Morning Run"

    def test_filter_multiple_matches(self):
        """Test filtering with multiple matches."""
        activities = [
            self.create_activity("Tempo Run"),
            self.create_activity("Tempo Workout"),
            self.create_activity("Easy Run"),
        ]

        filtered = filter_by_title(activities, "tempo")
        assert len(filtered) == 2


class TestFilterByRace:
    """Test race filtering."""

    def create_activity(
        self, activity_type: str, workout_type: int | None = None
    ) -> SummaryActivity:
        """Helper to create activity with specific type and workout type."""
        return SummaryActivity(
            id=1,
            name="Test Activity",
            distance=5000,
            moving_time=3600,
            elapsed_time=3600,
            total_elevation_gain=100.0,
            type=cast(ActivityType, activity_type),
            workout_type=workout_type,
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            start_date_local=datetime(2024, 1, 1, 0, 0, 0),
            timezone="(GMT+00:00) UTC",
            athlete=MetaAthlete(id=123),
        )

    def test_filter_races_only_run(self):
        """Test filtering for run races only."""
        activities = [
            self.create_activity("Run", workout_type=1),  # Race
            self.create_activity("Run", workout_type=0),  # Not race
            self.create_activity("Run"),  # No workout type
        ]

        filtered = filter_by_race(activities, is_race=True)
        assert len(filtered) == 1
        assert filtered[0].workout_type == 1

    def test_filter_races_only_ride(self):
        """Test filtering for ride races only."""
        activities = [
            self.create_activity("Ride", workout_type=11),  # Race
            self.create_activity("Ride", workout_type=0),  # Not race
            self.create_activity("Ride"),  # No workout type
        ]

        filtered = filter_by_race(activities, is_race=True)
        assert len(filtered) == 1
        assert filtered[0].workout_type == 11

    def test_filter_non_races(self):
        """Test filtering for non-races only."""
        activities = [
            self.create_activity("Run", workout_type=1),  # Race
            self.create_activity("Run", workout_type=0),  # Not race
            self.create_activity("Run"),  # No workout type
        ]

        filtered = filter_by_race(activities, is_race=False)
        assert len(filtered) == 2
        assert all(a.workout_type != 1 for a in filtered)

    def test_filter_race_mixed_types(self):
        """Test race filtering with mixed activity types."""
        activities = [
            self.create_activity("Run", workout_type=1),  # Run race
            self.create_activity("Ride", workout_type=11),  # Ride race
            self.create_activity("Run", workout_type=0),  # Not race
            self.create_activity("Swim"),  # No race detection for swim
        ]

        filtered = filter_by_race(activities, is_race=True)
        assert len(filtered) == 2
        assert filtered[0].type == "Run"
        assert filtered[1].type == "Ride"

    def test_filter_non_race_activity_without_race_detection(self):
        """Test that activity types without race detection are included in non-race filter."""
        activities = [
            self.create_activity("Swim"),  # No race detection
            self.create_activity("Walk"),  # No race detection
            self.create_activity("Run", workout_type=1),  # Race
        ]

        filtered = filter_by_race(activities, is_race=False)
        assert len(filtered) == 2
        assert filtered[0].type == "Swim"
        assert filtered[1].type == "Walk"

    def test_filter_race_activity_without_race_detection_excluded(self):
        """Test that activity types without race detection are excluded from race filter."""
        activities = [
            self.create_activity("Swim"),
            self.create_activity("Walk"),
            self.create_activity("Run", workout_type=1),
        ]

        filtered = filter_by_race(activities, is_race=True)
        assert len(filtered) == 1
        assert filtered[0].type == "Run"


class TestApplyFilters:
    """Test applying multiple filters."""

    def create_activity(
        self,
        name: str,
        activity_type: str,
        distance: float,
        workout_type: int | None = None,
    ) -> SummaryActivity:
        """Helper to create activity with all filter-relevant fields."""
        return SummaryActivity(
            id=1,
            name=name,
            distance=distance,
            moving_time=3600,
            elapsed_time=3600,
            total_elevation_gain=100.0,
            type=cast(ActivityType, activity_type),
            workout_type=workout_type,
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            start_date_local=datetime(2024, 1, 1, 0, 0, 0),
            timezone="(GMT+00:00) UTC",
            athlete=MetaAthlete(id=123),
        )

    def test_apply_multiple_filters(self):
        """Test applying multiple filters with AND logic."""
        activities = [
            self.create_activity("Parkrun Race", "Run", 5000, workout_type=1),
            self.create_activity("Morning Parkrun", "Run", 5000, workout_type=0),
            self.create_activity("Parkrun Race", "Ride", 5000, workout_type=11),
            self.create_activity("Long Run", "Run", 10000, workout_type=1),
        ]

        # Filter for: Run + 5k distance + parkrun in name + race
        filtered = apply_filters(
            activities,
            activity_type="Run",
            distance_min=4500,
            distance_max=5500,
            title_contains="parkrun",
            is_race=True,
        )

        assert len(filtered) == 1
        assert filtered[0].name == "Parkrun Race"
        assert filtered[0].type == "Run"

    def test_apply_no_filters(self):
        """Test that applying no filters returns all activities."""
        activities = [
            self.create_activity("Run 1", "Run", 5000),
            self.create_activity("Run 2", "Run", 10000),
        ]

        filtered = apply_filters(activities)
        assert len(filtered) == 2

    def test_apply_single_filter_activity_type(self):
        """Test applying only activity type filter."""
        activities = [
            self.create_activity("Run 1", "Run", 5000),
            self.create_activity("Ride 1", "Ride", 5000),
            self.create_activity("Run 2", "Run", 10000),
        ]

        filtered = apply_filters(activities, activity_type="Run")
        assert len(filtered) == 2
        assert all(a.type == "Run" for a in filtered)

    def test_apply_single_filter_distance(self):
        """Test applying only distance filter."""
        activities = [
            self.create_activity("Activity 1", "Run", 5000),
            self.create_activity("Activity 2", "Run", 10000),
            self.create_activity("Activity 3", "Run", 15000),
        ]

        filtered = apply_filters(activities, distance_min=9000, distance_max=11000)
        assert len(filtered) == 1
        assert filtered[0].distance == 10000

    def test_apply_single_filter_title(self):
        """Test applying only title filter."""
        activities = [
            self.create_activity("Morning Run", "Run", 5000),
            self.create_activity("Evening Run", "Run", 5000),
        ]

        filtered = apply_filters(activities, title_contains="morning")
        assert len(filtered) == 1
        assert filtered[0].name == "Morning Run"

    def test_apply_single_filter_race(self):
        """Test applying only race filter."""
        activities = [
            self.create_activity("Race", "Run", 5000, workout_type=1),
            self.create_activity("Training", "Run", 5000, workout_type=0),
        ]

        filtered = apply_filters(activities, is_race=True)
        assert len(filtered) == 1
        assert filtered[0].workout_type == 1

    def test_apply_filters_no_matches(self):
        """Test that filters with no matches return empty list."""
        activities = [
            self.create_activity("Run 1", "Run", 5000),
            self.create_activity("Run 2", "Run", 10000),
        ]

        # No activities match this criteria
        filtered = apply_filters(
            activities,
            activity_type="Swim",
        )
        assert len(filtered) == 0

    def test_apply_filters_empty_input(self):
        """Test applying filters to empty list."""
        filtered = apply_filters(
            [],
            activity_type="Run",
            distance_min=5000,
        )
        assert len(filtered) == 0
