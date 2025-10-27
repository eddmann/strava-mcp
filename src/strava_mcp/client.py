"""Strava API client with automatic token refresh and error handling."""

import types
from datetime import datetime
from typing import Any, Literal, Protocol

import httpx
from pydantic import TypeAdapter

from .models import (
    ActivityZone,
    Athlete,
    AthleteStats,
    Comment,
    DetailedActivity,
    DetailedSegment,
    Lap,
    Route,
    SegmentEffort,
    SegmentLeaderboard,
    SummaryActivity,
    SummaryAthlete,
    SummarySegment,
    Zones,
)


class StravaAuthContext(Protocol):
    """Common interface for accessing Strava credentials and refreshing tokens.

    This protocol defines the minimum interface required for authentication:
    - Access to current credentials (tokens, client ID/secret, preferences)
    - Ability to refresh tokens using mode-specific strategy
    """

    @property
    def strava_access_token(self) -> str:
        """Current Strava API access token."""
        ...

    @property
    def strava_client_id(self) -> str:
        """Strava OAuth application client ID."""
        ...

    @property
    def strava_client_secret(self) -> str:
        """Strava OAuth application client secret."""
        ...

    @property
    def strava_measurement_preference(self) -> Literal["meters", "feet"]:
        """User preference for distance/elevation units."""
        ...

    @property
    def route_export_path(self) -> str:
        """Directory path for exporting route files."""
        ...

    async def refresh_tokens(self) -> None:
        """Refresh Strava access token using mode-specific refresh strategy.

        Stdio mode: Calls Strava API, updates .env file
        HTTP mode: Calls OAuth service, updates session store
        """
        ...


class StravaAPIError(Exception):
    """Custom exception for Strava API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class StravaClient:
    """Async HTTP client for Strava API with automatic token refresh."""

    BASE_URL = "https://www.strava.com/api/v3"
    DEFAULT_PER_PAGE = 200  # Max allowed by Strava API
    DEFAULT_MAX_API_CALLS = 10  # Safety limit per request

    def __init__(self, context: StravaAuthContext):
        """Initialize the Strava API client."""
        self.context = context
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "StravaClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {"Authorization": f"Bearer {self.context.strava_access_token}"}

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an authenticated request to the Strava API.

        Automatically refreshes token on 401 and retries once.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            response = await self._client.request(
                method,
                endpoint,
                headers=headers,
                **kwargs,
            )

            # Handle 401 - token expired
            if response.status_code == 401:
                # Refresh tokens (mode-specific logic handled by context)
                await self.context.refresh_tokens()

                # Retry request with refreshed token
                headers = self._get_headers()
                response = await self._client.request(
                    method,
                    endpoint,
                    headers=headers,
                    **kwargs,
                )

            # Handle other errors
            if response.status_code == 402:
                raise StravaAPIError(
                    "This feature requires a Strava subscription. "
                    "Please upgrade your account at https://www.strava.com/settings/subscription",
                    402,
                )

            if response.status_code == 404:
                raise StravaAPIError(
                    "Resource not found. Please check the ID and try again.",
                    404,
                )

            if response.status_code == 429:
                raise StravaAPIError(
                    "Rate limit exceeded. Please try again later.",
                    429,
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            raise StravaAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise StravaAPIError(f"Request failed: {str(e)}") from e

    # Activity methods

    async def get_activities(
        self,
        before: datetime | None = None,
        after: datetime | None = None,
        start_page: int = 1,
        max_activities: int | None = None,
        activity_type: str | None = None,
        distance_min: int | None = None,
        distance_max: int | None = None,
        title_contains: str | None = None,
        is_race: bool | None = None,
    ) -> tuple[list[SummaryActivity], bool]:
        """Get activities with comprehensive client-side filtering.

        This method fetches activities from the Strava API and applies client-side
        filters iteratively until enough results are found or safety limits are hit.

        Args:
            before: Filter activities before this timestamp
            after: Filter activities after this timestamp
            start_page: Strava API page number to start from (for pagination)
            max_activities: Maximum number of filtered activities to return
            activity_type: Filter by activity type (e.g., 'Run', 'Ride')
            distance_min: Minimum distance in meters
            distance_max: Maximum distance in meters
            title_contains: Substring to search in activity names
            is_race: Filter by race status (True=races, False=non-races)

        Returns:
            Tuple of (filtered_activities, is_exhausted):
            - filtered_activities: List of filtered activities (up to max_activities)
            - is_exhausted: True if Strava has no more activities to fetch
                           False if we hit API safety limits or got enough results

        Note:
            Uses reduced safety limits with filters (5 API calls vs 10) to prevent
            excessive re-fetching when pagination is used. Each paginated request
            re-fetches from the beginning to handle client-side filtering correctly.
        """
        from .filters import apply_filters

        # Reduce API call limit when using client-side filters to prevent
        # excessive API usage during pagination (which re-fetches from start)
        has_filters = any(
            [activity_type, distance_min, distance_max, title_contains, is_race is not None]
        )
        max_api_calls = 5 if has_filters else self.DEFAULT_MAX_API_CALLS

        filtered_results: list[SummaryActivity] = []
        strava_page = start_page
        api_calls = 0
        is_exhausted = False

        params: dict[str, Any] = {"per_page": self.DEFAULT_PER_PAGE}
        if before:
            params["before"] = int(before.timestamp())
        if after:
            params["after"] = int(after.timestamp())

        # Keep fetching until we have enough results or hit limits
        while True:
            # Check termination conditions
            if api_calls >= max_api_calls:
                break

            if max_activities and len(filtered_results) >= max_activities:
                break

            # Fetch one page from Strava
            params["page"] = strava_page
            response = await self._request("GET", "/athlete/activities", params=params)
            adapter = TypeAdapter(list[SummaryActivity])
            raw_activities = adapter.validate_python(response.json())

            # No more activities from Strava
            if not raw_activities:
                is_exhausted = True
                break

            # Apply client-side filters
            filtered_batch = apply_filters(
                raw_activities,
                activity_type=activity_type,
                distance_min=distance_min,
                distance_max=distance_max,
                title_contains=title_contains,
                is_race=is_race,
            )

            # Add to results
            filtered_results.extend(filtered_batch)

            # Move to next page
            strava_page += 1
            api_calls += 1

        # Trim to requested limit
        if max_activities:
            filtered_results = filtered_results[:max_activities]

        return (filtered_results, is_exhausted)

    async def get_activity(self, activity_id: int) -> DetailedActivity:
        """Get detailed information about a specific activity."""
        response = await self._request("GET", f"/activities/{activity_id}")
        return DetailedActivity(**response.json())

    async def get_activity_streams(
        self,
        activity_id: int,
        keys: list[str] | None = None,
        key_by_type: bool = True,
    ) -> dict[str, Any]:
        """Get activity streams (time-series data)."""
        if keys is None:
            keys = [
                "time",
                "distance",
                "latlng",
                "altitude",
                "velocity_smooth",
                "heartrate",
                "cadence",
                "watts",
                "temp",
                "moving",
                "grade_smooth",
            ]

        response = await self._request(
            "GET",
            f"/activities/{activity_id}/streams",
            params={
                "keys": ",".join(keys),
                "key_by_type": str(key_by_type).lower(),
            },
        )
        return response.json()

    async def get_activity_laps(self, activity_id: int) -> list[Lap]:
        """Get laps for a specific activity."""
        response = await self._request("GET", f"/activities/{activity_id}/laps")
        adapter = TypeAdapter(list[Lap])
        return adapter.validate_python(response.json())

    async def get_activity_zones(self, activity_id: int) -> list[ActivityZone]:
        """Get zones for a specific activity."""
        response = await self._request("GET", f"/activities/{activity_id}/zones")
        adapter = TypeAdapter(list[ActivityZone])
        return adapter.validate_python(response.json())

    async def get_activity_comments(
        self,
        activity_id: int,
        page: int = 1,
        per_page: int = 30,
    ) -> list[Comment]:
        """Get comments for a specific activity."""
        response = await self._request(
            "GET",
            f"/activities/{activity_id}/comments",
            params={"page": page, "per_page": per_page},
        )
        adapter = TypeAdapter(list[Comment])
        return adapter.validate_python(response.json())

    async def get_activity_kudoers(
        self,
        activity_id: int,
        page: int = 1,
        per_page: int = 30,
    ) -> list[SummaryAthlete]:
        """Get athletes who gave kudos to a specific activity."""
        response = await self._request(
            "GET",
            f"/activities/{activity_id}/kudos",
            params={"page": page, "per_page": per_page},
        )
        adapter = TypeAdapter(list[SummaryAthlete])
        return adapter.validate_python(response.json())

    # Athlete methods

    async def get_athlete(self) -> Athlete:
        """Get the authenticated athlete's profile."""
        response = await self._request("GET", "/athlete")
        return Athlete(**response.json())

    async def get_athlete_stats(self, athlete_id: int) -> AthleteStats:
        """Get stats for a specific athlete."""
        response = await self._request("GET", f"/athletes/{athlete_id}/stats")
        return AthleteStats(**response.json())

    async def get_athlete_zones(self) -> Zones:
        """Get the authenticated athlete's heart rate and power zones."""
        response = await self._request("GET", "/athlete/zones")
        return Zones(**response.json())

    # Segment methods

    async def list_starred_segments(
        self,
        page: int = 1,
        per_page: int = 30,
    ) -> list[SummarySegment]:
        """List segments starred by the authenticated athlete."""
        response = await self._request(
            "GET",
            "/segments/starred",
            params={"page": page, "per_page": per_page},
        )
        adapter = TypeAdapter(list[SummarySegment])
        return adapter.validate_python(response.json())

    async def explore_segments(
        self,
        bounds: list[float],
        activity_type: str | None = None,
        min_cat: int | None = None,
        max_cat: int | None = None,
    ) -> dict[str, Any]:
        """Explore segments in a geographic area."""
        params: dict[str, Any] = {"bounds": ",".join(map(str, bounds))}
        if activity_type:
            params["activity_type"] = activity_type
        if min_cat is not None:
            params["min_cat"] = min_cat
        if max_cat is not None:
            params["max_cat"] = max_cat

        response = await self._request("GET", "/segments/explore", params=params)
        return response.json()

    async def get_segment(self, segment_id: int) -> DetailedSegment:
        """Get detailed information about a specific segment."""
        response = await self._request("GET", f"/segments/{segment_id}")
        return DetailedSegment(**response.json())

    async def star_segment(self, segment_id: int, starred: bool = True) -> DetailedSegment:
        """Star or unstar a segment."""
        response = await self._request(
            "PUT",
            f"/segments/{segment_id}/starred",
            json={"starred": starred},
        )
        return DetailedSegment(**response.json())

    async def get_segment_effort(self, effort_id: int) -> SegmentEffort:
        """Get detailed information about a specific segment effort."""
        response = await self._request("GET", f"/segment_efforts/{effort_id}")
        return SegmentEffort(**response.json())

    async def list_segment_efforts(
        self,
        segment_id: int,
        start_date_local: datetime | None = None,
        end_date_local: datetime | None = None,
        per_page: int = 30,
    ) -> list[SegmentEffort]:
        """List efforts for a specific segment."""
        params: dict[str, Any] = {"per_page": per_page}
        if start_date_local:
            params["start_date_local"] = start_date_local.isoformat()
        if end_date_local:
            params["end_date_local"] = end_date_local.isoformat()

        response = await self._request(
            "GET",
            f"/segments/{segment_id}/all_efforts",
            params=params,
        )
        adapter = TypeAdapter(list[SegmentEffort])
        return adapter.validate_python(response.json())

    async def get_segment_leaderboard(
        self,
        segment_id: int,
        gender: str | None = None,
        age_group: str | None = None,
        weight_class: str | None = None,
        following: bool | None = None,
        club_id: int | None = None,
        date_range: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> SegmentLeaderboard:
        """Get segment leaderboard with optional filters."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if gender:
            params["gender"] = gender
        if age_group:
            params["age_group"] = age_group
        if weight_class:
            params["weight_class"] = weight_class
        if following is not None:
            params["following"] = following
        if club_id:
            params["club_id"] = club_id
        if date_range:
            params["date_range"] = date_range

        response = await self._request(
            "GET",
            f"/segments/{segment_id}/leaderboard",
            params=params,
        )
        return SegmentLeaderboard(**response.json())

    # Route methods

    async def list_athlete_routes(
        self,
        athlete_id: int | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[Route]:
        """List routes for an athlete."""
        if athlete_id is None:
            # Get current athlete's ID
            athlete = await self.get_athlete()
            athlete_id = athlete.id

        response = await self._request(
            "GET",
            f"/athletes/{athlete_id}/routes",
            params={"page": page, "per_page": per_page},
        )
        adapter = TypeAdapter(list[Route])
        return adapter.validate_python(response.json())

    async def get_route(self, route_id: int) -> Route:
        """Get detailed information about a specific route."""
        response = await self._request("GET", f"/routes/{route_id}")
        return Route(**response.json())

    async def export_route_gpx(self, route_id: int) -> str:
        """Export a route as GPX format."""
        response = await self._request("GET", f"/routes/{route_id}/export_gpx")
        return response.text

    async def export_route_tcx(self, route_id: int) -> str:
        """Export a route as TCX format."""
        response = await self._request("GET", f"/routes/{route_id}/export_tcx")
        return response.text
