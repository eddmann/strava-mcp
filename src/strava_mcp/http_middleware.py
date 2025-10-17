"""Middleware for HTTP mode - OAuth-based multi-user authentication."""

from collections.abc import Callable
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.server.auth.middleware.auth_context import get_access_token

from .client import StravaClient
from .http_session import (
    HttpStravaAuthContext,
    SessionStore,
    StravaAppConfig,
    StravaOAuthService,
)


class HttpClientMiddleware(Middleware):
    """Middleware for HTTP mode - resolves session from OAuth token and creates StravaClient.

    This middleware:
    1. Extracts the OAuth access token from the MCP request
    2. Resolves the active user session from the SessionStore
    3. Creates a HttpStravaAuthContext combining app config + session
    4. Proactively refreshes Strava tokens if they're about to expire
    5. Creates a StravaClient instance and manages its lifecycle
    6. Injects the client into the context state for tools to access via ctx.get_state("client")
    7. Raises ToolError if authentication is missing or session has expired
    """

    def __init__(
        self,
        app_config: StravaAppConfig,
        session_store: SessionStore,
        oauth_service: StravaOAuthService,
    ) -> None:
        self.app_config = app_config
        self.session_store = session_store
        self.oauth_service = oauth_service

    async def on_call_tool(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Resolve session and inject StravaClient before every tool call."""
        # Get OAuth token from MCP request
        token = get_access_token()
        if token is None:
            raise ToolError("Authentication required. Please complete Strava OAuth first.")

        # Resolve session from token
        session = await self.session_store.get_session_by_token(token.token)
        if session is None:
            raise ToolError("Your Strava session has expired. Please re-authenticate.")

        # Create request context combining app config + session
        request_context = HttpStravaAuthContext(
            self.app_config,
            session,
            self.session_store,
            self.oauth_service,
        )

        # Proactively refresh Strava tokens if needed
        await request_context.ensure_active()

        # Create client and inject into context, managing lifecycle
        async with StravaClient(request_context) as client:
            if context.fastmcp_context:
                context.fastmcp_context.set_state("client", client)

            # Continue to the tool execution
            return await call_next(context)

    async def on_read_resource(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Resolve session and inject StravaClient before every resource read."""
        # Same logic as on_call_tool - resources also need authentication
        token = get_access_token()
        if token is None:
            raise ToolError("Authentication required. Please complete Strava OAuth first.")

        session = await self.session_store.get_session_by_token(token.token)
        if session is None:
            raise ToolError("Your Strava session has expired. Please re-authenticate.")

        request_context = HttpStravaAuthContext(
            self.app_config,
            session,
            self.session_store,
            self.oauth_service,
        )

        await request_context.ensure_active()

        async with StravaClient(request_context) as client:
            if context.fastmcp_context:
                context.fastmcp_context.set_state("client", client)

            return await call_next(context)
