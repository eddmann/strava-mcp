"""Stdio mode authentication - .env-based single-user credentials."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import set_key
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import TokenResponse


class StdioStravaAuthContext(BaseSettings):
    """Stdio mode: Strava API configuration from .env file.

    Single-user authentication where tokens are stored in and loaded from
    the .env file. Token refresh updates the .env file automatically.

    Implements StravaAuthContext protocol for compatibility with StravaClient.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_access_token: str = ""
    strava_refresh_token: str = ""
    strava_measurement_preference: Literal["meters", "feet"] = "meters"
    route_export_path: str = "./exports"

    @model_validator(mode="after")
    def validate_credentials(self) -> StdioStravaAuthContext:
        """Validate that required credentials are configured."""
        if not self.strava_client_id or self.strava_client_id == "your_client_id_here":
            raise ValueError(
                "Strava client ID not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )
        if not self.strava_client_secret or self.strava_client_secret == "your_client_secret_here":
            raise ValueError(
                "Strava client secret not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )
        if not self.strava_access_token or self.strava_access_token == "your_access_token_here":
            raise ValueError(
                "Strava access token not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )
        if not self.strava_refresh_token or self.strava_refresh_token == "your_refresh_token_here":
            raise ValueError(
                "Strava refresh token not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )
        return self

    async def refresh_tokens(self) -> None:
        """Refresh Strava access token and update .env file.

        This is the stdio-specific refresh strategy:
        1. Call Strava token endpoint with refresh_token
        2. Update .env file with new tokens
        3. Update this instance with new tokens
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": self.strava_client_id,
                    "client_secret": self.strava_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.strava_refresh_token,
                },
            )
            response.raise_for_status()
            token_data = TokenResponse(**response.json())

            # Update .env file
            _update_env_tokens(token_data.access_token, token_data.refresh_token)

            # Update this instance
            self.strava_access_token = token_data.access_token
            self.strava_refresh_token = token_data.refresh_token


def _update_env_tokens(access_token: str, refresh_token: str) -> None:
    """Update the .env file with new tokens.

    Args:
        access_token: New access token
        refresh_token: New refresh token
    """
    env_path = Path.cwd() / ".env"

    if not env_path.exists():
        # Create .env if it doesn't exist
        env_path.touch()

    # Update tokens in .env file
    set_key(str(env_path), "STRAVA_ACCESS_TOKEN", access_token)
    set_key(str(env_path), "STRAVA_REFRESH_TOKEN", refresh_token)

    # Also update environment variables for current process
    os.environ["STRAVA_ACCESS_TOKEN"] = access_token
    os.environ["STRAVA_REFRESH_TOKEN"] = refresh_token
