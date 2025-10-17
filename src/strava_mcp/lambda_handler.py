"""AWS Lambda handler for the Strava MCP server.

This module wraps the FastMCP ASGI app with Mangum for AWS Lambda deployment.
"""

from __future__ import annotations

from typing import Any

from mangum import Mangum

from .server import create_server


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    mcp = create_server("http")
    app = mcp.http_app(transport="streamable-http", stateless_http=True)
    mangum_handler = Mangum(app, lifespan="auto")

    return mangum_handler(event, context)
