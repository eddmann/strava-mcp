"""Local configuration wizard for Strava MCP transports."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Iterable
from getpass import getpass
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

from ..models import TokenResponse

DEFAULT_SCOPES = "profile:read_all,activity:read_all,activity:read,profile:write"
STDIO = "stdio"
HTTP = "http"


def main() -> None:
    """Run the interactive setup wizard for local Strava MCP configuration."""
    print("=" * 60)
    print("Strava MCP - Local Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard helps configure environment variables for stdio or http transport.")
    print("It will copy .env.example to .env (if needed) and update the relevant settings.")
    print()

    modes = _prompt_modes()
    if not modes:
        print("No transport selected. Exiting.")
        return

    env_path = _ensure_env_file()
    existing = dotenv_values(str(env_path)) if env_path.exists() else {}

    print()
    print("Step 1: Strava API credentials")
    print("-" * 60)
    print("Visit https://www.strava.com/settings/api and create an application if needed.")
    print("Use 'localhost' for the Authorization Callback Domain.")
    print()

    client_id = _prompt_required("Strava Client ID", existing.get("STRAVA_CLIENT_ID"))
    client_secret = _prompt_secret("Strava Client Secret", existing.get("STRAVA_CLIENT_SECRET"))

    set_key(str(env_path), "STRAVA_CLIENT_ID", client_id)
    set_key(str(env_path), "STRAVA_CLIENT_SECRET", client_secret)

    if STDIO in modes:
        _configure_stdio(env_path, client_id, client_secret)

    if HTTP in modes:
        _configure_http(env_path, existing)

    print("=" * 60)
    print("Configuration complete!")
    selected = " & ".join(sorted(modes))
    print(f"Updated .env for transport mode(s): {selected}")
    print("=" * 60)


def _prompt_modes() -> set[str]:
    """Prompt the user to choose which transport(s) to configure."""
    choices = {
        "1": {STDIO},
        "2": {HTTP},
        "3": {STDIO, HTTP},
    }
    print("Select transport mode to configure:")
    print("  1) stdio  (single-user tokens stored locally)")
    print("  2) http   (multi-user OAuth server)")
    print("  3) both")
    print()

    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice in choices:
            return choices[choice]
        print("Invalid selection. Please enter 1, 2, or 3.")


def _prompt_required(prompt_text: str, default: str | None = None) -> str:
    """Prompt for a required value, offering a default if provided."""
    while True:
        prompt = f"{prompt_text}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = input(prompt).strip()
        if value:
            return value
        if default:
            return default
        print("This value is required.")


def _prompt_secret(prompt_text: str, default: str | None = None) -> str:
    """Prompt for sensitive input (client secret)."""
    masked = "****" if default else None
    while True:
        prompt = f"{prompt_text}"
        if masked:
            prompt += " [press Enter to keep existing]"
        prompt += ": "
        value = getpass(prompt).strip()
        if value:
            return value
        if default:
            return default
        print("This value is required.")


def _prompt_optional(prompt_text: str, default: str | None = None) -> str | None:
    """Prompt for an optional value, returning None if left blank with no default."""
    prompt = f"{prompt_text}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    value = input(prompt).strip()
    if value:
        return value
    return default


def _ensure_env_file() -> Path:
    """Ensure .env exists, copying from .env.example if available."""
    env_path = Path.cwd() / ".env"
    example_path = Path.cwd() / ".env.example"
    if env_path.exists():
        return env_path

    if example_path.exists():
        shutil.copy(example_path, env_path)
        print(f"Created {env_path.name} from {example_path.name}")
    else:
        env_path.touch()
        print(f"Created empty {env_path.name} (no .env.example found)")
    return env_path


def _configure_stdio(env_path: Path, client_id: str, client_secret: str) -> None:
    """Run stdio setup, exchanging OAuth tokens and persisting them."""
    print()
    print("Step 2 (stdio): Authorize the application")
    print("-" * 60)

    print("Scopes requested for stdio mode:")
    print(f"  {DEFAULT_SCOPES}")
    print()

    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        "&response_type=code"
        "&redirect_uri=http://localhost"
        "&approval_prompt=force"
        f"&scope={DEFAULT_SCOPES}"
    )

    print("Open the following URL in your browser to authorize access:")
    print(auth_url)
    print()
    print("After authorization, Strava redirects to a URL like:")
    print("  http://localhost/?state=&code=XYZ&scope=...")
    print()

    redirect_url = input("Paste the full redirect URL: ").strip()
    if "code=" not in redirect_url:
        print("Error: Could not locate authorization code in the redirect URL.")
        return
    code = redirect_url.split("code=")[1].split("&")[0]

    print()
    print("Exchanging authorization code for tokens...")
    print("-" * 60)

    try:
        token_data = asyncio.run(_exchange_token(client_id, client_secret, code))
    except Exception as exc:  # noqa: BLE001 - surface any unexpected error
        print(f"Error: Failed to exchange code for tokens: {exc}")
        return

    if token_data is None:
        return

    set_key(str(env_path), "STRAVA_ACCESS_TOKEN", token_data.access_token)
    set_key(str(env_path), "STRAVA_REFRESH_TOKEN", token_data.refresh_token)

    print()
    print("✓ stdio tokens saved to .env")
    if token_data.athlete:
        athlete = token_data.athlete
        name = f"{athlete.firstname} {athlete.lastname}".strip()
        if name:
            print(f"Authenticated as: {name}")
    print()


def _configure_http(env_path: Path, existing: dict[str, str | None]) -> None:
    """Prompt for HTTP transport environment settings."""
    print()
    print("Step 2 (http): Configure HTTP transport settings")
    print("-" * 60)

    host = _prompt_optional(
        "Server host (STRAVA_MCP_HOST)",
        existing.get("STRAVA_MCP_HOST") or "127.0.0.1",
    )
    port = _prompt_optional(
        "Server port (STRAVA_MCP_PORT)",
        existing.get("STRAVA_MCP_PORT") or "8000",
    )
    base_url = _prompt_optional(
        "Public base URL (STRAVA_MCP_BASE_URL) [leave blank for auto]",
        existing.get("STRAVA_MCP_BASE_URL") or "",
    )
    http_path = _prompt_optional(
        "Path prefix (STRAVA_MCP_PATH)",
        existing.get("STRAVA_MCP_PATH") or "/mcp",
    )

    measurement = _prompt_optional(
        "Measurement preference (meters|feet)",
        existing.get("STRAVA_MEASUREMENT_PREFERENCE") or "meters",
    )
    export_path = _prompt_optional(
        "Route export path (ROUTE_EXPORT_PATH)",
        existing.get("ROUTE_EXPORT_PATH") or "./exports",
    )

    scopes = _prompt_optional(
        "OAuth scopes (STRAVA_OAUTH_SCOPES)",
        existing.get("STRAVA_OAUTH_SCOPES") or DEFAULT_SCOPES,
    )
    clients = _prompt_optional(
        "Registered MCP clients (STRAVA_MCP_OAUTH_CLIENTS)",
        existing.get("STRAVA_MCP_OAUTH_CLIENTS"),
    )

    backend = _prompt_optional(
        "Session backend (memory|dynamodb)",
        existing.get("STRAVA_SESSION_BACKEND") or "memory",
    )

    dynamo_table = dynamo_region = ttl_seconds = None
    if backend and backend.lower() == "dynamodb":
        print()
        print("DynamoDB configuration:")
        dynamo_table = _prompt_optional(
            "Table name (STRAVA_SESSION_TABLE)",
            existing.get("STRAVA_SESSION_TABLE"),
        )
        dynamo_region = _prompt_optional(
            "AWS region (AWS_REGION/AWS_DEFAULT_REGION)",
            existing.get("AWS_REGION") or existing.get("AWS_DEFAULT_REGION"),
        )
        ttl_seconds = _prompt_optional(
            "Session TTL seconds (STRAVA_SESSION_TTL_SECONDS)",
            existing.get("STRAVA_SESSION_TTL_SECONDS"),
        )

    _set_keys(
        env_path,
        (
            ("STRAVA_MCP_HOST", host),
            ("STRAVA_MCP_PORT", port),
            ("STRAVA_MCP_BASE_URL", base_url or None),
            ("STRAVA_MCP_PATH", http_path),
            ("STRAVA_MEASUREMENT_PREFERENCE", measurement),
            ("ROUTE_EXPORT_PATH", export_path),
            ("STRAVA_OAUTH_SCOPES", scopes),
            ("STRAVA_MCP_OAUTH_CLIENTS", clients),
            ("STRAVA_SESSION_BACKEND", backend),
            ("STRAVA_SESSION_TABLE", dynamo_table),
            ("AWS_REGION", dynamo_region),
            ("STRAVA_SESSION_TTL_SECONDS", ttl_seconds),
        ),
    )

    print()
    print("✓ HTTP environment values updated.")
    print("Remember to install HTTP dependencies: pip install '.[http]'")
    print()


def _set_keys(env_path: Path, pairs: Iterable[tuple[str, str | None]]) -> None:
    """Persist non-empty key/value pairs to the .env file."""
    for key, value in pairs:
        if value is None:
            continue
        set_key(str(env_path), key, value)


async def _exchange_token(
    client_id: str,
    client_secret: str,
    code: str,
) -> TokenResponse | None:
    """Exchange authorization code for tokens using Strava's OAuth endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )

        if response.status_code != 200:
            print(
                f"Error: Token exchange failed with status {response.status_code}",
            )
            print(response.text)
            return None

        return TokenResponse(**response.json())


if __name__ == "__main__":
    main()
