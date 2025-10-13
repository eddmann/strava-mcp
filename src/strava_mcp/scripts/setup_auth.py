"""Interactive OAuth setup script for Strava MCP."""

import asyncio
from pathlib import Path

import httpx
from dotenv import set_key

from ..models import TokenResponse


def main():
    """Run the interactive OAuth setup."""
    print("=" * 60)
    print("Strava MCP - OAuth Setup")
    print("=" * 60)
    print()
    print("This script will help you set up OAuth authentication with Strava.")
    print()

    # Step 1: Get client credentials
    print("Step 1: Get your Strava API credentials")
    print("-" * 60)
    print("1. Go to https://www.strava.com/settings/api")
    print("2. Create a new application if you haven't already")
    print("3. Set the Authorization Callback Domain to 'localhost'")
    print()

    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()

    if not client_id or not client_secret:
        print("\nError: Client ID and Client Secret are required.")
        return

    # Step 2: Authorization URL
    print()
    print("Step 2: Authorize the application")
    print("-" * 60)

    # Scopes needed for all features
    scopes = "profile:read_all,activity:read_all,activity:read,profile:write"

    # Build authorization URL
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri=http://localhost"
        f"&approval_prompt=force"
        f"&scope={scopes}"
    )

    print("Please visit this URL to authorize the application:")
    print()
    print(auth_url)
    print()
    print("After authorizing, you will be redirected to a localhost URL.")
    print("The URL will look like: http://localhost/?state=&code=XXXXX&scope=...")
    print()

    redirect_url = input("Paste the full redirect URL here: ").strip()

    # Extract authorization code from URL
    if "code=" not in redirect_url:
        print("\nError: Invalid redirect URL. Could not find authorization code.")
        return

    code = redirect_url.split("code=")[1].split("&")[0]

    # Step 3: Exchange code for tokens
    print()
    print("Step 3: Exchanging authorization code for tokens...")
    print("-" * 60)

    try:
        asyncio.run(exchange_token(client_id, client_secret, code))
    except Exception as e:
        print(f"\nError: Failed to exchange code for tokens: {str(e)}")
        return


async def exchange_token(client_id: str, client_secret: str, code: str):
    """Exchange authorization code for access and refresh tokens."""
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
            print(f"\nError: Token exchange failed with status {response.status_code}")
            print(response.text)
            return

        token_data = TokenResponse(**response.json())

        # Save to .env file
        env_path = Path.cwd() / ".env"

        if not env_path.exists():
            env_path.touch()

        set_key(str(env_path), "STRAVA_CLIENT_ID", client_id)
        set_key(str(env_path), "STRAVA_CLIENT_SECRET", client_secret)
        set_key(str(env_path), "STRAVA_ACCESS_TOKEN", token_data.access_token)
        set_key(str(env_path), "STRAVA_REFRESH_TOKEN", token_data.refresh_token)

        print("\n✓ Success! Tokens have been saved to .env")
        print()

        if token_data.athlete:
            print(f"Authenticated as: {token_data.athlete.firstname} {token_data.athlete.lastname}")

        print()
        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("You can now use the Strava MCP server.")
        print("Run: strava-mcp")
        print()


if __name__ == "__main__":
    main()
