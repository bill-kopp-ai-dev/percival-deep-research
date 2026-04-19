FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files for dependency resolution
COPY pyproject.toml .
COPY README.md .

# Install dependencies via uv (without dev extras)
RUN uv sync --no-dev

# Copy application code
COPY . .

# Environment variables for Docker runtime
ENV MCP_TRANSPORT=sse
ENV DOCKER_CONTAINER=true
ENV PYTHONUNBUFFERED=1

# Default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=7s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the server via uv
CMD ["uv", "run", "gptr-mcp"]
