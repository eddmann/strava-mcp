"""Pytest configuration and shared fixtures."""

import pytest
import respx
from httpx import Response


@pytest.fixture
def mock_config():
    """Provide a mock Strava configuration for testing."""
    from strava_mcp.auth import StravaConfig

    return StravaConfig(
        strava_client_id="test_client_id",
        strava_client_secret="test_client_secret",
        strava_access_token="test_access_token",
        strava_refresh_token="test_refresh_token",
        strava_measurement_preference="meters",
        route_export_path="/tmp/strava_routes",
    )


@pytest.fixture
def respx_mock():
    """Provide a respx mock router for HTTP requests."""
    with respx.mock(
        base_url="https://www.strava.com/api/v3", assert_all_called=False
    ) as respx_mock:
        yield respx_mock


@pytest.fixture
def stub_strava_api(respx_mock):
    """Provide a stubbed Strava API with common response helpers."""

    class StravaAPIStub:
        """Helper class for stubbing Strava API responses."""

        def __init__(self, respx_mock):
            self.respx_mock = respx_mock
            self.base_url = "https://www.strava.com/api/v3"

        def stub_get_athlete(self, athlete_data=None, status_code=200):
            """Stub GET /athlete endpoint."""
            if athlete_data is None:
                athlete_data = {
                    "id": 123456,
                    "username": "test_athlete",
                    "resource_state": 3,
                    "firstname": "Test",
                    "lastname": "Athlete",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "US",
                    "sex": "M",
                    "premium": True,
                    "summit": True,
                    "created_at": "2017-11-14T02:30:05.000Z",
                    "updated_at": "2018-02-06T19:32:20.000Z",
                    "measurement_preference": "meters",
                    "ftp": 250,
                    "weight": 75.0,
                }

            self.respx_mock.get("/athlete").mock(
                return_value=Response(status_code, json=athlete_data)
            )
            return athlete_data

        def stub_error(self, endpoint, method="GET", status_code=404, error_message=None):
            """Stub an error response."""
            error_data = {"message": error_message or "Not Found", "errors": []}

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

        def stub_paginated_endpoint(self, endpoint, data_list, page=1, per_page=30):
            """Stub a paginated endpoint."""
            start = (page - 1) * per_page
            end = start + per_page
            page_data = data_list[start:end]

            self.respx_mock.get(endpoint).mock(return_value=Response(200, json=page_data))
            return page_data

    return StravaAPIStub(respx_mock)
