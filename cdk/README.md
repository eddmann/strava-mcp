# Strava MCP CDK Deployment

Infrastructure as code for the Strava MCP server lives in this directory. The stack provisions:

- AWS Lambda running the MCP service with Mangum
- DynamoDB table for session storage
- Public Lambda Function URL

## Prerequisites

- Python 3.11+
- [AWS CDK v2](https://docs.aws.amazon.com/cdk/latest/guide/home.html) CLI (`npm install -g aws-cdk`)
- Docker (required for the bundling process that builds the Lambda artifact)
- AWS credentials configured with permissions for CloudFormation, Lambda, DynamoDB, and IAM role creation

## Setup

1. Install dependencies with uv:
   ```sh
   uv sync
   ```
2. Copy `config.py.example` to `config.py` and fill in the Strava OAuth secrets plus any extra environment variables you need:
   ```sh
   cp config.py.example config.py
   ```
   Values placed in `config.py` will be merged into the Lambda environment.

## Synthesis & Deployment

1. Bootstrap the target AWS environment once per account/region (skip if already bootstrapped):
   ```sh
   uv run cdk bootstrap
   ```
2. Synthesize the CloudFormation template to verify everything resolves:
   ```sh
   uv run cdk synth
   ```
3. Deploy the stack:
   ```sh
   uv run cdk deploy
   ```
   Outputs include the public Lambda Function URL and DynamoDB table name.

## Post-Deployment Notes

- Deleting the stack currently destroys the DynamoDB table. Adjust the removal policy if you need to retain session data.
- To update the Lambda environment (e.g., new secrets or settings), change `config.py` and redeploy.
