"""Type definitions for structured JSON responses.

This module defines TypedDict classes for the structured JSON responses
returned by all MCP tools. These types improve type safety and IDE support.
"""

from typing import Any, NotRequired, TypedDict


# Basic value types with formatting
class FormattedDistance(TypedDict):
    """Distance with raw and formatted values."""

    meters: float
    formatted: str


class FormattedDuration(TypedDict):
    """Duration with raw and formatted values."""

    seconds: int
    formatted: str


class FormattedSpeed(TypedDict):
    """Speed with raw and formatted values."""

    meters_per_second: float
    formatted: str


class FormattedPace(TypedDict):
    """Pace with raw and formatted values."""

    seconds_per_km: float
    formatted: str


class FormattedElevation(TypedDict):
    """Elevation with raw and formatted values."""

    meters: float
    formatted: str


class FormattedHeartRate(TypedDict):
    """Heart rate with raw and formatted values."""

    bpm: float
    formatted: str


class FormattedPower(TypedDict):
    """Power with raw and formatted values."""

    watts: float
    formatted: str


# Response structure types
class ResponseMetadata(TypedDict, total=False):
    """Metadata included in all responses."""

    fetched_at: str
    query_type: str
    # Allow any additional metadata fields
    # Note: TypedDict doesn't support arbitrary keys, so we use total=False


class ResponseAnalysis(TypedDict, total=False):
    """Analysis section of responses."""

    insights: list[str]
    summary: str
    # Allow any additional analysis fields


class BaseResponse(TypedDict):
    """Base structure for all tool responses."""

    data: dict[str, Any]  # Main data payload varies by tool
    metadata: ResponseMetadata
    analysis: NotRequired[ResponseAnalysis]


class ErrorDetail(TypedDict):
    """Error information in error responses."""

    message: str
    type: str
    timestamp: str
    suggestions: NotRequired[list[str]]


class ErrorResponse(TypedDict):
    """Structure for error responses."""

    error: ErrorDetail


# Activity-specific types
class FormattedActivityData(TypedDict, total=False):
    """Formatted activity data structure."""

    id: int
    name: str
    type: str
    sport_type: str
    start_date: str
    distance: FormattedDistance
    time: FormattedDuration
    moving_time: FormattedDuration
    elapsed_time: FormattedDuration
    pace: FormattedPace
    speed: FormattedSpeed
    elevation_gain: FormattedElevation
    average_heartrate: FormattedHeartRate
    max_heartrate: FormattedHeartRate
    average_power: FormattedPower
    max_power: FormattedPower
    normalized_power: FormattedPower
    calories: float
    kudos_count: int
    comment_count: int


class FormattedLapData(TypedDict, total=False):
    """Formatted lap data structure."""

    lap_index: int
    distance: FormattedDistance
    time: FormattedDuration
    moving_time: FormattedDuration
    elapsed_time: FormattedDuration
    pace: FormattedPace
    speed: FormattedSpeed
    average_speed: FormattedSpeed
    max_speed: FormattedSpeed
    elevation_gain: FormattedElevation
    average_heartrate: FormattedHeartRate
    max_heartrate: FormattedHeartRate
    average_cadence: float
    average_power: FormattedPower


# Segment-specific types
class FormattedSegmentData(TypedDict, total=False):
    """Formatted segment data structure."""

    id: int
    name: str
    activity_type: str
    distance: FormattedDistance
    average_grade: float
    maximum_grade: float
    elevation_high: FormattedElevation
    elevation_low: FormattedElevation
    total_elevation_gain: FormattedElevation
    climb_category: int
    city: str
    state: str
    country: str
    private: bool
    hazardous: bool
    starred: bool
    effort_count: int
    athlete_count: int
    star_count: int


# Route-specific types
class FormattedRouteData(TypedDict, total=False):
    """Formatted route data structure."""

    id: int
    name: str
    description: str
    distance: FormattedDistance
    elevation_gain: FormattedElevation
    type: int
    sub_type: int
    private: bool
    starred: bool
    timestamp: int


# Athlete-specific types
class FormattedAthleteProfile(TypedDict, total=False):
    """Formatted athlete profile structure."""

    id: int
    username: str
    firstname: str
    lastname: str
    city: str
    state: str
    country: str
    sex: str
    premium: bool
    created_at: str
    updated_at: str
    weight: float
    ftp: int
    measurement_preference: str


# Aggregated metrics types
class AggregatedMetrics(TypedDict, total=False):
    """Aggregated metrics across multiple activities."""

    total_distance: FormattedDistance
    total_time: FormattedDuration
    total_elevation_gain: FormattedElevation
    total_activities: int
    average_distance: FormattedDistance
    average_time: FormattedDuration
    average_pace: FormattedPace
    average_speed: FormattedSpeed
