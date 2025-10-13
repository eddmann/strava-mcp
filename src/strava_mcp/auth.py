"""OAuth authentication and token management for Strava API."""

import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv, set_key
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import TokenResponse


class StravaConfig(BaseSettings):
    """Strava API configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_access_token: str = ""
    strava_refresh_token: str = ""
    strava_measurement_preference: Literal["meters", "feet"] = "meters"
    route_export_path: str = "./exports"


def load_config() -> StravaConfig:
    """Load configuration from .env file."""
    load_dotenv()
    return StravaConfig()


def validate_credentials(config: StravaConfig) -> bool:
    """Check if credentials are properly configured."""
    if not config.strava_client_id or config.strava_client_id == "your_client_id_here":
        return False
    if not config.strava_client_secret or config.strava_client_secret == "your_client_secret_here":
        return False
    if not config.strava_access_token or config.strava_access_token == "your_access_token_here":
        return False
    if not config.strava_refresh_token or config.strava_refresh_token == "your_refresh_token_here":
        return False
    return True


async def refresh_access_token(config: StravaConfig) -> tuple[str, str]:
    """
    Refresh the Strava access token using the refresh token.

    Returns:
        Tuple of (new_access_token, new_refresh_token)

    Raises:
        httpx.HTTPError: If the refresh request fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": config.strava_client_id,
                "client_secret": config.strava_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": config.strava_refresh_token,
            },
        )
        response.raise_for_status()

        token_data = TokenResponse(**response.json())
        return token_data.access_token, token_data.refresh_token


def update_env_tokens(access_token: str, refresh_token: str) -> None:
    """
    Update the .env file with new tokens.

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
