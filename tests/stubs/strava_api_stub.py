"""Comprehensive Strava API stubbing helpers using respx."""

from httpx import Response


class StravaAPIStubber:
    """Helper class for stubbing Strava API responses with respx."""

    def __init__(self, respx_mock):
        """Initialize with a respx mock instance."""
        self.respx_mock = respx_mock

    def stub_athlete_endpoint(self, athlete_data, status_code=200):
        """Stub GET /athlete endpoint."""
        self.respx_mock.get("/athlete").mock(
            return_value=Response(status_code, json=athlete_data)
        )

    def stub_athlete_stats_endpoint(self, athlete_id, stats_data, status_code=200):
        """Stub GET /athletes/{id}/stats endpoint."""
        self.respx_mock.get(f"/athletes/{athlete_id}/stats").mock(
            return_value=Response(status_code, json=stats_data)
        )

    def stub_athlete_zones_endpoint(self, zones_data, status_code=200):
        """Stub GET /athlete/zones endpoint."""
        self.respx_mock.get("/athlete/zones").mock(
            return_value=Response(status_code, json=zones_data)
        )

    def stub_activities_endpoint(self, activities_data, status_code=200, page=None, per_page=None):
        """Stub GET /athlete/activities endpoint with optional pagination."""
        if page is not None and per_page is not None:
            self.respx_mock.get(
                "/athlete/activities",
                params={"page": page, "per_page": per_page}
            ).mock(return_value=Response(status_code, json=activities_data))
        else:
            self.respx_mock.get("/athlete/activities").mock(
                return_value=Response(status_code, json=activities_data)
            )

    def stub_activity_details_endpoint(self, activity_id, activity_data, status_code=200):
        """Stub GET /activities/{id} endpoint."""
        self.respx_mock.get(f"/activities/{activity_id}").mock(
            return_value=Response(status_code, json=activity_data)
        )

    def stub_activity_streams_endpoint(self, activity_id, streams_data, status_code=200):
        """Stub GET /activities/{id}/streams endpoint."""
        self.respx_mock.get(f"/activities/{activity_id}/streams").mock(
            return_value=Response(status_code, json=streams_data)
        )

    def stub_activity_laps_endpoint(self, activity_id, laps_data, status_code=200):
        """Stub GET /activities/{id}/laps endpoint."""
        self.respx_mock.get(f"/activities/{activity_id}/laps").mock(
            return_value=Response(status_code, json=laps_data)
        )

    def stub_starred_segments_endpoint(self, segments_data, status_code=200):
        """Stub GET /segments/starred endpoint."""
        self.respx_mock.get("/segments/starred").mock(
            return_value=Response(status_code, json=segments_data)
        )

    def stub_explore_segments_endpoint(self, segments_data, status_code=200):
        """Stub GET /segments/explore endpoint."""
        self.respx_mock.get("/segments/explore").mock(
            return_value=Response(status_code, json=segments_data)
        )

    def stub_segment_details_endpoint(self, segment_id, segment_data, status_code=200):
        """Stub GET /segments/{id} endpoint."""
        self.respx_mock.get(f"/segments/{segment_id}").mock(
            return_value=Response(status_code, json=segment_data)
        )

    def stub_star_segment_endpoint(self, segment_id, segment_data, status_code=200):
        """Stub PUT /segments/{id}/starred endpoint."""
        self.respx_mock.put(f"/segments/{segment_id}/starred").mock(
            return_value=Response(status_code, json=segment_data)
        )

    def stub_segment_effort_endpoint(self, effort_id, effort_data, status_code=200):
        """Stub GET /segment_efforts/{id} endpoint."""
        self.respx_mock.get(f"/segment_efforts/{effort_id}").mock(
            return_value=Response(status_code, json=effort_data)
        )

    def stub_segment_efforts_endpoint(self, segment_id, efforts_data, status_code=200):
        """Stub GET /segments/{id}/all_efforts endpoint."""
        self.respx_mock.get(f"/segments/{segment_id}/all_efforts").mock(
            return_value=Response(status_code, json=efforts_data)
        )

    def stub_routes_endpoint(self, athlete_id, routes_data, status_code=200):
        """Stub GET /athletes/{id}/routes endpoint."""
        self.respx_mock.get(f"/athletes/{athlete_id}/routes").mock(
            return_value=Response(status_code, json=routes_data)
        )

    def stub_route_details_endpoint(self, route_id, route_data, status_code=200):
        """Stub GET /routes/{id} endpoint."""
        self.respx_mock.get(f"/routes/{route_id}").mock(
            return_value=Response(status_code, json=route_data)
        )

    def stub_route_export_gpx_endpoint(self, route_id, gpx_data, status_code=200):
        """Stub GET /routes/{id}/export_gpx endpoint."""
        self.respx_mock.get(f"/routes/{route_id}/export_gpx").mock(
            return_value=Response(status_code, text=gpx_data)
        )

    def stub_route_export_tcx_endpoint(self, route_id, tcx_data, status_code=200):
        """Stub GET /routes/{id}/export_tcx endpoint."""
        self.respx_mock.get(f"/routes/{route_id}/export_tcx").mock(
            return_value=Response(status_code, text=tcx_data)
        )

    def stub_error_response(self, endpoint, method="GET", status_code=404, message="Not Found"):
        """Stub an error response for any endpoint."""
        error_data = {
            "message": message,
            "errors": []
        }

        if method == "GET":
            self.respx_mock.get(endpoint).mock(
                return_value=Response(status_code, json=error_data)
            )
        elif method == "PUT":
            self.respx_mock.put(endpoint).mock(
                return_value=Response(status_code, json=error_data)
            )
        elif method == "POST":
            self.respx_mock.post(endpoint).mock(
                return_value=Response(status_code, json=error_data)
            )
