#!/usr/bin/env python3
"""CDK application entry point for the Strava MCP infrastructure."""

from __future__ import annotations

import os

import aws_cdk as cdk

from strava_mcp import StravaMcpStack


def main() -> None:
    app = cdk.App()
    env = cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "eu-west-1"),
    )
    StravaMcpStack(app, "StravaMcpStack", env=env)
    app.synth()


if __name__ == "__main__":
    main()
