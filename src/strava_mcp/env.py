"""Environment file locations for Strava MCP configuration."""

from pathlib import Path

DEFAULT_ENV_FILE = Path.home() / ".strava-mcp.env"
LOCAL_ENV_FILE = Path(".env")


def get_env_file_path() -> Path:
    """Get the env file path interactive setup should write to."""
    local_env = Path.cwd() / LOCAL_ENV_FILE
    if local_env.exists():
        return local_env
    return DEFAULT_ENV_FILE


def get_env_files() -> tuple[str, str]:
    """Return env files in precedence order for settings loaders."""
    return (str(DEFAULT_ENV_FILE), str(LOCAL_ENV_FILE))
