"""Analysis tools for Strava MCP server.

This module provides higher-level analysis tools that transform raw Strava data
into actionable insights.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastmcp import Context

from ..auth import StravaConfig
from ..client import StravaAPIError, StravaClient
from ..models import MeasurementPreference
from ..response_builder import ResponseBuilder
from ..time_utils import get_range_description, parse_time_range


async def analyze_training(
    period: Annotated[
        str,
        "Time period to analyze. Options: '7d', '30d', '90d', 'ytd', 'this-week', "
        "'this-month', or 'YYYY-MM-DD:YYYY-MM-DD'",
    ] = "30d",
    activity_type: Annotated[
        str | None, "Filter by activity type (e.g., 'Run', 'Ride', 'Swim')"
    ] = None,
    max_activities: Annotated[
        int,
        "Max activities to analyze (1-500, default 200). Higher values may be slow.",
    ] = 200,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Analyze training over a period with aggregated metrics and trends.

    This tool provides comprehensive training analysis including:
    - Aggregated metrics (distance, time, elevation)
    - Weekly breakdown and trends
    - Activity type distribution
    - Basic insights

    Returns: JSON string with structure:
    {
        "data": {
            "period": {
                "description": "Last 30 days",
                "start_date": "2024-12-15",
                "end_date": "2025-01-15",
                "days": 31
            },
            "summary": {
                "total_activities": 15,
                "total_distance": {...},
                "total_time": {...},
                "total_elevation": {...},
                "averages": {
                    "distance_per_activity": {...},
                    "activities_per_week": 3.5
                }
            },
            "by_activity_type": [
                {"type": "Run", "count": 12, "percentage": 80},
                ...
            ],
            "trends": {
                "weekly": [
                    {"week_start": "2024-12-09", "activities": 4, "distance_meters": 40000},
                    ...
                ]
            }
        },
        "analysis": {
            "insights": [...]
        },
        "metadata": {
            "fetched_at": "ISO timestamp"
        }
    }
    """
    assert ctx is not None
    config: StravaConfig = ctx.get_state("config")

    # Validate max_activities
    if max_activities < 1 or max_activities > 500:
        return ResponseBuilder.build_error_response(
            f"Invalid max_activities: {max_activities}. Must be between 1 and 500.",
            error_type="validation_error",
        )

    try:
        # Parse time range
        start, end = parse_time_range(period)

        async with StravaClient(config) as client:
            if activity_type:
                activities = await client.get_activities_by_type(
                    activity_type=activity_type,
                    after=start,
                    before=end,
                    per_page=200,
                    max_activities=max_activities,
                    max_api_calls=min(10, (max_activities // 50) + 2),
                )
            else:
                activities = await client.get_all_activities(
                    after=start,
                    before=end,
                    per_page=200,
                    max_activities=max_activities,
                )

            if not activities:
                metadata = {"period": get_range_description(period)}
                if activity_type:
                    metadata["activity_type"] = activity_type

                return ResponseBuilder.build_response(
                    {
                        "period": {
                            "description": get_range_description(period),
                            "start_date": start.strftime("%Y-%m-%d"),
                            "end_date": end.strftime("%Y-%m-%d"),
                            "days": (end - start).days,
                        },
                        "summary": {"total_activities": 0},
                        "message": "No activities found in this period",
                    },
                    metadata=metadata,
                )

            # Calculate period info
            period_days = (end - start).days + 1
            period_weeks = period_days / 7

            # Aggregate metrics
            total_distance = sum(a.distance for a in activities)
            total_time = sum(a.moving_time for a in activities)
            total_elevation = sum(a.total_elevation_gain for a in activities)

            # Activity type distribution
            type_counts: defaultdict[str, int] = defaultdict(int)
            type_distance: defaultdict[str, float] = defaultdict(float)
            for activity in activities:
                type_counts[activity.type] += 1
                type_distance[activity.type] += activity.distance

            by_type: list[dict[str, Any]] = [
                {
                    "type": activity_type,
                    "count": count,
                    "percentage": round((count / len(activities)) * 100, 1),
                    "distance": {
                        "meters": type_distance[activity_type],
                        "formatted": f"{type_distance[activity_type] / 1000:.1f} km"
                        if unit == "meters"
                        else f"{type_distance[activity_type] * 0.000621371:.1f} mi",
                    },
                }
                for activity_type, count in sorted(
                    type_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]

            # Weekly breakdown
            weekly_data: defaultdict[str, dict[str, int | float]] = defaultdict(
                lambda: {"count": 0, "distance": 0.0, "time": 0}
            )
            for activity in activities:
                # Get week start (Monday)
                # activity.start_date_local is already a datetime object from Pydantic model
                activity_date = activity.start_date_local
                week_start = activity_date - timedelta(days=activity_date.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                week_dict = weekly_data[week_key]
                week_dict["count"] = int(week_dict["count"]) + 1  # type: ignore
                week_dict["distance"] = float(week_dict["distance"]) + activity.distance  # type: ignore
                week_dict["time"] = int(week_dict["time"]) + activity.moving_time  # type: ignore

            weekly_trends: list[dict[str, Any]] = [
                {
                    "week_start": week,
                    "activities": data["count"],
                    "distance": {
                        "meters": data["distance"],
                        "formatted": f"{data['distance'] / 1000:.1f} km"
                        if unit == "meters"
                        else f"{data['distance'] * 0.000621371:.1f} mi",
                    },
                    "time": {
                        "seconds": data["time"],
                        "formatted": f"{data['time'] // 3600}h {(data['time'] % 3600) // 60}m",
                    },
                }
                for week, data in sorted(weekly_data.items())
            ]

            # Build response
            response_data: dict[str, Any] = {
                "period": {
                    "description": get_range_description(period),
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "days": period_days,
                },
                "summary": {
                    "total_activities": len(activities),
                    "total_distance": {
                        "meters": total_distance,
                        "formatted": f"{total_distance / 1000:.1f} km"
                        if unit == "meters"
                        else f"{total_distance * 0.000621371:.1f} mi",
                    },
                    "total_time": {
                        "seconds": total_time,
                        "formatted": f"{total_time // 3600}h {(total_time % 3600) // 60}m",
                    },
                    "total_elevation": {
                        "meters": total_elevation,
                        "formatted": f"{total_elevation:.0f} m"
                        if unit == "meters"
                        else f"{total_elevation * 3.28084:.0f} ft",
                    },
                    "averages": {
                        "distance_per_activity": {
                            "meters": total_distance / len(activities),
                            "formatted": f"{total_distance / len(activities) / 1000:.1f} km"
                            if unit == "meters"
                            else f"{total_distance / len(activities) * 0.000621371:.1f} mi",
                        },
                        "activities_per_week": round(len(activities) / period_weeks, 1),
                    },
                },
                "by_activity_type": by_type,
                "trends": {"weekly": weekly_trends},
            }

            # Generate insights
            insights: list[str] = []

            # Activity count insight
            if len(activities) >= period_weeks * 5:
                insights.append(
                    f"High training volume: {len(activities)} activities in {period_days} days"
                )
            elif len(activities) <= period_weeks * 2:
                insights.append(
                    f"Low training volume: {len(activities)} activities in {period_days} days"
                )

            # Weekly trend
            if len(weekly_trends) >= 2:
                # type: ignore
                first_week_distance = weekly_trends[0]["distance"]["meters"]
                # type: ignore
                last_week_distance = weekly_trends[-1]["distance"]["meters"]
                if float(last_week_distance) > float(first_week_distance) * 1.2:
                    insights.append("Training volume increasing over time")
                elif float(last_week_distance) < float(first_week_distance) * 0.8:
                    insights.append("Training volume decreasing over time")

            # Activity type diversity
            if len(by_type) == 1:
                insights.append(f"Training focused on {by_type[0]['type']}")
            elif len(by_type) >= 3:
                insights.append("Good activity type diversity")

            analysis: dict[str, Any] = {"insights": insights}

            metadata = {
                "period": get_range_description(period),
                "time_range_parsed": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            }

            if activity_type:
                metadata["activity_type"] = activity_type

            return ResponseBuilder.build_response(
                response_data, analysis=analysis, metadata=metadata
            )

    except ValueError as e:
        return ResponseBuilder.build_error_response(
            str(e),
            error_type="validation_error",
        )
    except StravaAPIError as e:
        error_type = "api_error"
        if e.status_code == 429:
            error_type = "rate_limit"

        return ResponseBuilder.build_error_response(
            e.message,
            error_type=error_type,
        )
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}",
            error_type="internal_error",
        )


async def compare_activities(
    activity_ids: Annotated[str, "Comma-separated activity IDs to compare (2-5 activities)"],
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Compare multiple activities side-by-side.

    Returns: JSON string with structure:
    {
        "data": {
            "activities": [
                {
                    "id": 12345,
                    "name": "Morning Run",
                    "metrics": {...}
                },
                ...
            ],
            "comparison": {
                "distance": {
                    "fastest": {"id": 12345, "value": {...}},
                    "slowest": {"id": 12346, "value": {...}}
                },
                ...
            }
        },
        "analysis": {
            "insights": [...]
        },
        "metadata": {
            "fetched_at": "ISO timestamp"
        }
    }
    """
    assert ctx is not None
    config: StravaConfig = ctx.get_state("config")

    try:
        # Parse activity IDs
        ids = [int(id.strip()) for id in activity_ids.split(",")]

        if len(ids) < 2:
            return ResponseBuilder.build_error_response(
                "Must provide at least 2 activity IDs to compare",
                error_type="validation_error",
            )

        if len(ids) > 5:
            return ResponseBuilder.build_error_response(
                "Can only compare up to 5 activities at once",
                error_type="validation_error",
            )

        async with StravaClient(config) as client:
            # Fetch activities
            activities_data: list[Any] = []
            for activity_id in ids:
                activity = await client.get_activity(activity_id)
                activities_data.append(activity)

            # Format activities
            formatted_activities: list[dict[str, Any]] = []
            for activity in activities_data:
                activity_dict = activity.model_dump()
                formatted = ResponseBuilder.format_activity(activity_dict, unit)
                formatted_activities.append(formatted)

            # Build comparison
            comparison: dict[str, Any] = {}

            # Distance comparison
            if all("distance" in a for a in formatted_activities):
                distances: list[tuple[Any, Any]] = [
                    (a["id"], a["distance"]["meters"]) for a in formatted_activities
                ]
                longest: tuple[Any, Any] = max(distances, key=lambda x: x[1])
                shortest: tuple[Any, Any] = min(distances, key=lambda x: x[1])
                comparison["distance"] = {
                    "longest": {
                        "id": longest[0],
                        "meters": longest[1],
                        "formatted": f"{longest[1] / 1000:.2f} km"
                        if unit == "meters"
                        else f"{longest[1] * 0.000621371:.2f} mi",
                    },
                    "shortest": {
                        "id": shortest[0],
                        "meters": shortest[1],
                        "formatted": f"{shortest[1] / 1000:.2f} km"
                        if unit == "meters"
                        else f"{shortest[1] * 0.000621371:.2f} mi",
                    },
                }

            # Pace comparison (for similar distances)
            if all("time" in a and "distance" in a for a in formatted_activities):
                times = [
                    (a["id"], a["time"]["moving_seconds"], a["distance"]["meters"])
                    for a in formatted_activities
                ]
                fastest = min(times, key=lambda x: x[1])
                slowest = max(times, key=lambda x: x[1])
                comparison["time"] = {
                    "fastest": {
                        "id": fastest[0],
                        "seconds": fastest[1],
                        "formatted": f"{fastest[1] // 60}:{fastest[1] % 60:02d}",
                    },
                    "slowest": {
                        "id": slowest[0],
                        "seconds": slowest[1],
                        "formatted": f"{slowest[1] // 60}:{slowest[1] % 60:02d}",
                    },
                }

            # Heart rate comparison
            hr_activities = [a for a in formatted_activities if "heart_rate" in a]
            if hr_activities:
                hr_data = [(a["id"], a["heart_rate"]["avg_bpm"]) for a in hr_activities]
                highest = max(hr_data, key=lambda x: x[1])
                lowest = min(hr_data, key=lambda x: x[1])
                comparison["heart_rate"] = {
                    "highest_avg": {"id": highest[0], "bpm": highest[1]},
                    "lowest_avg": {"id": lowest[0], "bpm": lowest[1]},
                }

            data = {
                "activities": formatted_activities,
                "comparison": comparison,
            }

            # Generate insights
            insights: list[str] = []

            # Check if activities are same type
            types = set(a["type"] for a in formatted_activities)
            if len(types) == 1:
                insights.append(f"All activities are {list(types)[0]} type")
            else:
                insights.append(f"Comparing different activity types: {', '.join(types)}")

            analysis: dict[str, list[str]] = {"insights": insights}

            return ResponseBuilder.build_response(
                data, analysis=analysis, metadata={"activity_ids": ids}
            )

    except ValueError as e:
        return ResponseBuilder.build_error_response(
            f"Invalid activity IDs: {str(e)}",
            error_type="validation_error",
        )
    except StravaAPIError as e:
        error_type = "api_error"
        if e.status_code == 404:
            error_type = "not_found"
        elif e.status_code == 429:
            error_type = "rate_limit"

        return ResponseBuilder.build_error_response(
            e.message,
            error_type=error_type,
        )
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}",
            error_type="internal_error",
        )


async def find_similar_activities(
    activity_id: Annotated[int, "Reference activity ID"],
    criteria: Annotated[
        str,
        "Similarity criteria (comma-separated: 'type', 'distance', 'elevation', 'duration')",
    ] = "type,distance",
    limit: Annotated[int, "Max similar activities to return (1-20, default 10)"] = 10,
    search_days: Annotated[int, "Days to search back (1-365, default 90)"] = 90,
    unit: Annotated[MeasurementPreference, "Unit preference ('meters' or 'feet')"] = "meters",
    ctx: Context | None = None,
) -> str:
    """Find activities similar to a reference activity.

    This tool helps track progress by finding similar workouts over time.

    Returns: JSON string with structure:
    {
        "data": {
            "reference_activity": {...},
            "similar_activities": [
                {
                    "activity": {...},
                    "similarity_score": 0.95,
                    "differences": {...}
                },
                ...
            ]
        },
        "metadata": {
            "fetched_at": "ISO timestamp"
        }
    }
    """
    assert ctx is not None
    config: StravaConfig = ctx.get_state("config")

    # Validate inputs
    if limit < 1 or limit > 20:
        return ResponseBuilder.build_error_response(
            f"Invalid limit: {limit}. Must be between 1 and 20.",
            error_type="validation_error",
        )
    if search_days < 1 or search_days > 365:
        return ResponseBuilder.build_error_response(
            f"Invalid search_days: {search_days}. Must be between 1 and 365.",
            error_type="validation_error",
        )

    try:
        # Parse criteria
        criteria_list = [c.strip().lower() for c in criteria.split(",")]
        valid_criteria = {"type", "distance", "elevation", "duration"}
        invalid = set(criteria_list) - valid_criteria
        if invalid:
            return ResponseBuilder.build_error_response(
                f"Invalid criteria: {', '.join(invalid)}. Valid: {', '.join(valid_criteria)}",
                error_type="validation_error",
            )

        async with StravaClient(config) as client:
            # Get reference activity
            reference = await client.get_activity(activity_id)

            # Get recent activities with reduced search window
            start = datetime.now() - timedelta(days=search_days)
            activities = await client.get_all_activities(
                after=start,
                per_page=200,
                max_activities=300,
                max_api_calls=3,
            )

            # Filter out reference activity
            activities = [a for a in activities if a.id != activity_id]

            # Calculate similarity scores
            from ..models import SummaryActivity

            scored_activities: list[tuple[SummaryActivity, float]] = []
            for activity in activities:
                score = 0.0
                max_score = 0.0

                # Type similarity
                if "type" in criteria_list:
                    max_score += 1
                    if activity.type == reference.type:
                        score += 1

                # Distance similarity (within 10%)
                if "distance" in criteria_list:
                    max_score += 1
                    if reference.distance > 0:
                        distance_diff = (
                            abs(activity.distance - reference.distance) / reference.distance
                        )
                        if distance_diff <= 0.1:
                            score += 1
                        elif distance_diff <= 0.2:
                            score += 0.5

                # Elevation similarity (within 20%)
                if "elevation" in criteria_list:
                    max_score += 1
                    if reference.total_elevation_gain > 0:
                        elev_diff = (
                            abs(activity.total_elevation_gain - reference.total_elevation_gain)
                            / reference.total_elevation_gain
                        )
                        if elev_diff <= 0.2:
                            score += 1
                        elif elev_diff <= 0.4:
                            score += 0.5

                # Duration similarity (within 15%)
                if "duration" in criteria_list:
                    max_score += 1
                    if reference.moving_time > 0:
                        time_diff = (
                            abs(activity.moving_time - reference.moving_time)
                            / reference.moving_time
                        )
                        if time_diff <= 0.15:
                            score += 1
                        elif time_diff <= 0.3:
                            score += 0.5

                if max_score > 0:
                    similarity_score = score / max_score
                    if similarity_score > 0.5:  # Only include reasonably similar activities
                        scored_activities.append((activity, similarity_score))

            # Sort by similarity score
            scored_activities.sort(key=lambda x: x[1], reverse=True)
            top_activities = scored_activities[:limit]

            # Format results
            reference_formatted = ResponseBuilder.format_activity(reference.model_dump(), unit)

            similar: list[dict[str, Any]] = []
            for activity, score in top_activities:
                activity_formatted = ResponseBuilder.format_activity(activity.model_dump(), unit)

                # Calculate differences
                differences = {}
                if "distance" in criteria_list and reference.distance > 0:
                    diff_m = activity.distance - reference.distance
                    diff_pct = (diff_m / reference.distance) * 100
                    differences["distance"] = {
                        "diff_meters": diff_m,
                        "diff_percent": round(diff_pct, 1),
                    }

                if "duration" in criteria_list and reference.moving_time > 0:
                    diff_s = activity.moving_time - reference.moving_time
                    diff_pct = (diff_s / reference.moving_time) * 100
                    differences["time"] = {
                        "diff_seconds": diff_s,
                        "diff_percent": round(diff_pct, 1),
                    }

                similar.append(
                    {
                        "activity": activity_formatted,
                        "similarity_score": round(score, 2),
                        "differences": differences,
                    }
                )

            data = {
                "reference_activity": reference_formatted,
                "similar_activities": similar,
                "count": len(similar),
            }

            metadata = {
                "reference_activity_id": activity_id,
                "criteria": criteria_list,
                "limit": limit,
            }

            return ResponseBuilder.build_response(data, metadata=metadata)

    except StravaAPIError as e:
        error_type = "api_error"
        if e.status_code == 404:
            error_type = "not_found"
        elif e.status_code == 429:
            error_type = "rate_limit"

        return ResponseBuilder.build_error_response(
            e.message,
            error_type=error_type,
        )
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}",
            error_type="internal_error",
        )
