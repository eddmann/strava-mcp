"""Middleware for Strava MCP server.

This module provides middleware components that run before tool execution.
"""

from collections.abc import Callable
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from .auth import load_config, validate_credentials
from .client import StravaClient


class ClientMiddleware(Middleware):
    """Middleware that creates and injects StravaClient for all tool calls.

    This middleware:
    1. Loads the Strava config from environment variables
    2. Validates that credentials are properly configured
    3. Creates a StravaClient instance and manages its lifecycle
    4. Injects the client into the context state for tools to access via ctx.get_state("client")
    5. Raises ToolError if authentication is not configured
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Create and inject StravaClient before every tool call."""
        # Load configuration from environment
        config = load_config()

        # Validate credentials are properly configured
        if not validate_credentials(config):
            raise ToolError(
                "Strava credentials not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )

        # Create client and inject into context, managing lifecycle
        async with StravaClient(config) as client:
            if context.fastmcp_context:
                context.fastmcp_context.set_state("client", client)

            # Continue to the tool execution
            return await call_next(context)
