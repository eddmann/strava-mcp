# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-20

### Added

- Initial Strava MCP server release
- Strava activity, athlete, segment, route, and analysis tools
- MCP resource for athlete profile context
- MCP prompts for training analysis, segment performance, activity analysis, run comparison, training summary, and race performance
- `strava-mcp` server entrypoint with stdio and HTTP transport modes
- `strava-mcp auth` interactive OAuth setup with token persistence
- Docker image support via GitHub Container Registry
- AWS Lambda and CDK deployment support for HTTP mode

[1.0.0]: https://github.com/eddmann/strava-mcp/releases/tag/v1.0.0
