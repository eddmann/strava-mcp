"""Middleware for Strava MCP server.

This module provides middleware components that run before tool execution.
"""

from collections.abc import Callable
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from .auth import load_config, validate_credentials


class ConfigMiddleware(Middleware):
    """Middleware that loads and validates Strava configuration for all tool calls.

    This middleware:
    1. Loads the Strava config from environment variables
    2. Validates that credentials are properly configured
    3. Injects the config into the context state for tools to access via ctx.get_state("config")
    4. Raises ToolError if authentication is not configured
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Load and validate config before every tool call."""
        # Load configuration from environment
        config = load_config()

        # Validate credentials are properly configured
        if not validate_credentials(config):
            raise ToolError(
                "Strava credentials not configured. "
                "Please run 'strava-mcp-auth' to set up authentication."
            )

        # Inject config into context state for tools to access
        if context.fastmcp_context:
            context.fastmcp_context.set_state("config", config)

        # Continue to the tool execution
        return await call_next(context)
