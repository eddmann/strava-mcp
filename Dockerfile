# Multi-stage build for minimal final image
FROM python:3.11-slim AS builder

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev

# Final stage - minimal runtime image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create directory for token storage
RUN mkdir -p /app/.strava_tokens

# Expose MCP server
# The server runs via stdio, so no port exposure needed

# Health check (optional - checks if Python and dependencies are available)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import strava_mcp; print('ok')" || exit 1

# Run the MCP server
ENTRYPOINT ["python", "-m", "strava_mcp.server"]
