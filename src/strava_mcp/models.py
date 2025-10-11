"""Pydantic models for Strava API responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Type aliases for common enums
Sex = Literal["M", "F"]
MeasurementPreference = Literal["feet", "meters"]
ActivityType = Literal[
    "AlpineSki",
    "BackcountrySki",
    "Canoeing",
    "Crossfit",
    "EBikeRide",
    "Elliptical",
    "Golf",
    "Handcycle",
    "Hike",
    "IceSkate",
    "InlineSkate",
    "Kayaking",
    "Kitesurf",
    "NordicSki",
    "Ride",
    "RockClimbing",
    "RollerSki",
    "Rowing",
    "Run",
    "Sail",
    "Skateboard",
    "Snowboard",
    "Snowshoe",
    "Soccer",
    "StairStepper",
    "StandUpPaddling",
    "Surfing",
    "Swim",
    "Velomobile",
    "VirtualRide",
    "VirtualRun",
    "Walk",
    "WeightTraining",
    "Wheelchair",
    "Windsurf",
    "Workout",
    "Yoga",
]
SportType = Literal["cycling", "running", "triathlon", "other"]
ClubMembership = Literal["member", "pending"]


# Base Meta models
class MetaAthlete(BaseModel):
    """Minimal athlete representation in other resources."""

    id: int
    resource_state: int | None = None


class MetaActivity(BaseModel):
    """Minimal activity representation in other resources."""

    id: int
    resource_state: int | None = None


class MetaClub(BaseModel):
    """Minimal club representation."""

    id: int
    resource_state: int | None = None
    name: str | None = None


# Gear models
class SummaryGear(BaseModel):
    """Summary representation of gear (bike or shoes)."""

    id: str
    resource_state: int | None = None
    primary: bool | None = None
    name: str | None = None
    distance: float | None = None


class DetailedGear(SummaryGear):
    """Detailed gear with additional information."""

    brand_name: str | None = None
    model_name: str | None = None
    frame_type: int | None = None  # Bike only
    description: str | None = None


# Club models
class SummaryClub(MetaClub):
    """Summary representation of a club."""

    profile_medium: str | None = None
    cover_photo: str | None = None
    cover_photo_small: str | None = None
    sport_type: SportType | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    private: bool | None = None
    member_count: int | None = None
    featured: bool | None = None
    verified: bool | None = None
    url: str | None = None


class DetailedClub(SummaryClub):
    """Detailed club with membership information."""

    membership: ClubMembership | None = None
    admin: bool | None = None
    owner: bool | None = None
    following_count: int | None = None


# Comment model
class Comment(BaseModel):
    """Comment on an activity."""

    id: int
    activity_id: int
    text: str | None = None
    athlete: "SummaryAthlete | None" = None
    created_at: datetime | None = None


# Photo models
class PhotoUrls(BaseModel):
    """URLs for different photo sizes."""

    model_config = {"extra": "allow"}  # Allow additional URL sizes


class PrimaryPhoto(BaseModel):
    """Primary photo information."""

    id: int | None = None
    source: int | None = None
    unique_id: str | None = None
    urls: dict[str, str] | None = None


class PhotosSummary(BaseModel):
    """Summary of photos for an activity."""

    count: int | None = None
    primary: PrimaryPhoto | None = None


# Split model
class Split(BaseModel):
    """Activity split information."""

    average_speed: float | None = None
    distance: float | None = None
    elapsed_time: int | None = None
    elevation_difference: float | None = None
    pace_zone: int | None = None
    moving_time: int | None = None
    split: int | None = None


# Athlete segment stats model
class AthleteSegmentStats(BaseModel):
    """Personal records and stats for a segment."""

    pr_elapsed_time: int | None = None
    pr_date: datetime | None = None
    effort_count: int | None = None


# Achievement model
class Achievement(BaseModel):
    """Achievement earned on a segment effort."""

    type_id: int | None = None
    type: str | None = None
    rank: int | None = None


# Zone models
class ZoneRange(BaseModel):
    """A range defining a training zone."""

    min: int | None = None
    max: int | None = None


class TimedZoneRange(ZoneRange):
    """Zone range with time spent in zone."""

    time: int | None = None  # Seconds spent in this zone


class ActivityZone(BaseModel):
    """Activity zone data (heart rate or power)."""

    score: int | None = None
    distribution_buckets: list[TimedZoneRange] | None = None
    type: Literal["heartrate", "power"] | None = None
    sensor_based: bool | None = None
    points: int | None = None
    custom_zones: bool | None = None
    max: int | None = None


# Athlete models (forward reference resolved below)
class SummaryAthlete(MetaAthlete):
    """Summary athlete representation."""

    firstname: str | None = None
    lastname: str | None = None
    profile_medium: str | None = None
    profile: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    sex: Sex | None = None
    premium: bool | None = None
    summit: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Athlete(SummaryAthlete):
    """Detailed athlete profile (also known as DetailedAthlete in the API)."""

    username: str | None = None
    bio: str | None = None
    badge_type_id: int | None = None
    weight: float | None = None
    friend: bool | None = None
    follower: bool | None = None
    follower_count: int | None = None
    friend_count: int | None = None
    measurement_preference: MeasurementPreference | None = None
    ftp: int | None = None
    clubs: list[SummaryClub] | None = None
    bikes: list[SummaryGear] | None = None
    shoes: list[SummaryGear] | None = None


class ActivityStats(BaseModel):
    """Statistics for a specific activity type."""

    count: int
    distance: float
    moving_time: int
    elapsed_time: int
    elevation_gain: float
    achievement_count: int | None = None


class AthleteStats(BaseModel):
    """Comprehensive athlete statistics."""

    biggest_ride_distance: float | None = None
    biggest_climb_elevation_gain: float | None = None
    recent_ride_totals: ActivityStats
    recent_run_totals: ActivityStats
    recent_swim_totals: ActivityStats
    ytd_ride_totals: ActivityStats
    ytd_run_totals: ActivityStats
    ytd_swim_totals: ActivityStats
    all_ride_totals: ActivityStats
    all_run_totals: ActivityStats
    all_swim_totals: ActivityStats


class PolylineMap(BaseModel):
    """Map with encoded polyline."""

    id: str
    polyline: str | None = None
    summary_polyline: str | None = None
    resource_state: int | None = None


class SummaryActivity(MetaActivity):
    """Summary representation of an activity."""

    name: str
    distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    type: ActivityType
    sport_type: ActivityType | None = None
    athlete: MetaAthlete | None = None
    external_id: str | None = None
    upload_id: int | None = None
    start_date: datetime
    start_date_local: datetime
    timezone: str
    achievement_count: int | None = None
    kudos_count: int | None = None
    comment_count: int | None = None
    athlete_count: int | None = None
    photo_count: int | None = None
    map: PolylineMap | None = None
    trainer: bool | None = None
    commute: bool | None = None
    manual: bool | None = None
    private: bool | None = None
    visibility: str | None = None
    flagged: bool | None = None
    gear_id: str | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    has_heartrate: bool | None = None
    average_heartrate: float | None = None
    max_heartrate: int | None = None
    heartrate_opt_out: bool | None = None
    display_hide_heartrate_option: bool | None = None
    upload_id: int | None = None
    external_id: str | None = None
    pr_count: int | None = None
    total_photo_count: int | None = None
    workout_type: int | None = None


class DetailedActivity(SummaryActivity):
    """Detailed activity with additional information."""

    description: str | None = None
    calories: float | None = None
    device_name: str | None = None
    embed_token: str | None = None
    splits_metric: list[Split] | None = None
    splits_standard: list[Split] | None = None
    laps: list["Lap"] | None = None  # Forward reference
    gear: SummaryGear | None = None
    partner_brand_tag: str | None = None
    photos: PhotosSummary | None = None
    highlighted_kudosers: list[SummaryAthlete] | None = None
    device_watts: bool | None = None
    has_kudoed: bool | None = None
    segment_efforts: list["SegmentEffort"] | None = None  # Forward reference
    best_efforts: list["SegmentEffort"] | None = None  # Forward reference
    average_watts: float | None = None
    weighted_average_watts: int | None = None
    kilojoules: float | None = None
    max_watts: int | None = None
    elev_high: float | None = None
    elev_low: float | None = None


class StreamSet(BaseModel):
    """A set of activity streams."""

    time: list[int] | None = None
    distance: list[float] | None = None
    latlng: list[list[float]] | None = None
    altitude: list[float] | None = None
    velocity_smooth: list[float] | None = None
    heartrate: list[int] | None = None
    cadence: list[int] | None = None
    watts: list[int] | None = None
    temp: list[int] | None = None
    moving: list[bool] | None = None
    grade_smooth: list[float] | None = None


class Lap(BaseModel):
    """Activity lap information."""

    id: int
    name: str | None = None
    activity: MetaActivity | None = None
    athlete: MetaAthlete | None = None
    elapsed_time: int
    moving_time: int
    start_date: datetime
    start_date_local: datetime
    distance: float
    start_index: int | None = None
    end_index: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_cadence: float | None = None
    average_watts: float | None = None
    average_heartrate: float | None = None
    max_heartrate: int | None = None
    lap_index: int | None = None
    split: int | None = None
    pace_zone: int | None = None
    device_watts: bool | None = None
    resource_state: int | None = None


class SummarySegment(BaseModel):
    """Summary representation of a segment."""

    id: int
    name: str
    activity_type: str
    distance: float
    average_grade: float
    maximum_grade: float
    elevation_high: float
    elevation_low: float
    start_latlng: list[float] | None = None
    end_latlng: list[float] | None = None
    climb_category: int
    city: str | None = None
    state: str | None = None
    country: str | None = None
    private: bool
    hazardous: bool | None = None
    starred: bool | None = None
    resource_state: int | None = None


class DetailedSegment(SummarySegment):
    """Detailed segment with additional information."""

    created_at: datetime | None = None
    updated_at: datetime | None = None
    total_elevation_gain: float | None = None
    map: PolylineMap | None = None
    effort_count: int | None = None
    athlete_count: int | None = None
    star_count: int | None = None
    athlete_segment_stats: AthleteSegmentStats | None = None


class SegmentEffort(BaseModel):
    """Segment effort information."""

    id: int
    name: str
    activity: MetaActivity | None = None
    athlete: MetaAthlete | None = None
    elapsed_time: int
    moving_time: int
    start_date: datetime
    start_date_local: datetime
    distance: float
    start_index: int | None = None
    end_index: int | None = None
    average_cadence: float | None = None
    average_watts: float | None = None
    device_watts: bool | None = None
    average_heartrate: float | None = None
    max_heartrate: int | None = None
    segment: SummarySegment | None = None
    kom_rank: int | None = None
    pr_rank: int | None = None
    achievements: list[Achievement] | None = None
    hidden: bool | None = None
    resource_state: int | None = None


class Route(BaseModel):
    """Route information."""

    id: int
    name: str
    description: str | None = None
    athlete: MetaAthlete | None = None
    distance: float
    elevation_gain: float
    map: PolylineMap | None = None
    type: int | None = None
    sub_type: int | None = None
    private: bool | None = None
    starred: bool | None = None
    timestamp: int | None = None
    segments: list[SummarySegment] | None = None
    estimated_moving_time: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id_str: str | None = None
    resource_state: int | None = None


class HeartRateZoneRanges(BaseModel):
    """Heart rate zone ranges."""

    custom_zones: bool
    zones: list[ZoneRange]


class PowerZoneRanges(BaseModel):
    """Power zone ranges."""

    zones: list[ZoneRange]


class Zones(BaseModel):
    """Athlete training zones."""

    heart_rate: HeartRateZoneRanges | None = None
    power: PowerZoneRanges | None = None


class TokenResponse(BaseModel):
    """OAuth token response."""

    token_type: str
    expires_at: int
    expires_in: int
    refresh_token: str
    access_token: str
    athlete: Athlete | None = None
