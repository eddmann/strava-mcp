"""CDK stack that deploys the Strava MCP server to AWS Lambda."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import aws_cdk as cdk
from aws_cdk import BundlingOptions, Duration, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_


def _load_lambda_env_overrides() -> dict[str, str]:
    """Load optional Lambda environment overrides from config.py if present."""
    try:
        from config import LAMBDA_ENV_OVERRIDES  # type: ignore
    except ImportError:
        return {}

    overrides = LAMBDA_ENV_OVERRIDES
    if not isinstance(overrides, Mapping):
        raise TypeError("LAMBDA_ENV_OVERRIDES must be a mapping of string keys to values.")

    return {str(key): str(value) for key, value in overrides.items()}


class StravaMcpStack(cdk.Stack):
    """Provision the Strava MCP server, DynamoDB session store, and Lambda URL."""

    def __init__(self, scope: cdk.App, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_root = Path(__file__).resolve().parents[2]

        table = dynamodb.Table(
            self,
            "StravaSessionTable",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        lambda_code = lambda_.Code.from_asset(
            path=str(project_root),
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                command=[
                    "bash",
                    "-lc",
                    "pip install '.[http]' -t /asset-output && "
                    "find /asset-output -name '*.pyc' -delete && "
                    "find /asset-output -type d -name '__pycache__' -exec rm -rf {} +",
                ],
                environment={
                    "PIP_NO_CACHE_DIR": "1",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                },
            ),
        )

        lambda_env: dict[str, str] = {
            "STRAVA_SESSION_BACKEND": "dynamodb",
            "STRAVA_SESSION_TABLE": table.table_name,
            "STRAVA_SESSION_TTL_SECONDS": str(10 * 24 * 60 * 60),
            "STRAVA_MCP_PATH": "/mcp",
        }
        lambda_env.update(_load_lambda_env_overrides())

        lambda_fn = lambda_.Function(
            self,
            "StravaMcpFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="strava_mcp.lambda_handler.handler",
            code=lambda_code,
            timeout=Duration.seconds(30),
            memory_size=1024,
            architecture=lambda_.Architecture.ARM_64,
            environment=lambda_env,
        )

        table.grant_read_write_data(lambda_fn)

        lambda_url = lambda_fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.ALL],
                allowed_headers=["*"],
            ),
        )

        cdk.CfnOutput(
            self,
            "LambdaFunctionUrl",
            value=lambda_url.url,
        )

        cdk.CfnOutput(
            self,
            "SessionTableName",
            value=table.table_name,
        )
