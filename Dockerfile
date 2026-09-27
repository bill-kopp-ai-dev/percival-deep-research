# syntax=docker/dockerfile:1.7
#
# Percival Deep Research — MCP server image.
#
# Multi-stage build:
#   1. `builder`  — uv (ghcr.io/astral-sh/uv) installs Python deps,
#                   installs this project as a wheel, and applies the
#                   gpt-researcher `NameError: name 'Any'` patch
#                   (mandatory for gpt-researcher >= 0.16.0).
#   2. `runtime`  — minimal `python:3.11-slim`, copies the prepared venv,
#                   runs as non-root `percival` (UID 1000), default
#                   transport is `stdio` (compatible with Nanobot,
#                   OpenCode, and the Docker MCP gateway).
#
# The container speaks JSON-RPC over stdin/stdout by default. Override
# with `MCP_TRANSPORT=sse` or `MCP_TRANSPORT=streamable-http` for HTTP.

# ──────────────────────────────────────────────────────────────────────
# Stage 1: builder
# ──────────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# uv tuning — cache byte-code in the venv (slightly larger image, faster
# runtime import), never download Python interpreters (we use the bundled
# one), and prefer `copy` link mode for predictable layer diffs.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

# Copy ONLY the metadata needed to resolve dependencies first, so source
# edits don't bust the dependency layer.
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install deps without installing the project itself (fast path).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --frozen

# Now copy the full source tree and install the project (so the
# `percival-deep-research` console script is registered in the venv).
COPY . .

# Install this project as a package + apply the gpt-researcher patch.
# The patch is mandatory: without it, the runtime crashes at first
# import of gpt_researcher.actions.query_processing with
# `NameError: name 'Any' is not defined` on Python 3.11/3.12.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen \
    && uv run --no-sync python scripts/patch_gpt_researcher.py

# ──────────────────────────────────────────────────────────────────────
# Stage 2: runtime
# ──────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# OCI / MCP catalog metadata — queryable via `docker inspect` and
# required for the Docker MCP Catalog (hub.docker.com/mcp).
LABEL org.opencontainers.image.title="percival-deep-research" \
      org.opencontainers.image.description="Multi-source web research and report generation MCP server, optimized for the Nanobot agent ecosystem." \
      org.opencontainers.image.source="https://github.com/bill-kopp-ai-dev/percival.OS" \
      org.opencontainers.image.documentation="https://github.com/bill-kopp-ai-dev/percival.OS/blob/main/percival-deep-research/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="percival.OS contributors" \
      org.opencontainers.image.version="3.0.1" \
      io.modelcontextprotocol.server.name="percival-deep-research"

# Runtime essentials: curl for HEALTHCHECK, tini for proper signal
# forwarding (PID 1 must reap zombies and forward SIGTERM).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (UID 1000 matches the convention used by HKUDS/nanobot).
RUN groupadd --system --gid 1000 percival \
    && useradd  --system --uid 1000 --gid percival \
        --home-dir /app --shell /usr/sbin/nologin percival \
    && mkdir -p /app/reports /app/logs /app/.cache \
    && chown -R percival:percival /app

WORKDIR /app

# Copy the prepared venv + project source from the builder.
COPY --from=builder --chown=percival:percival /app /app

# Runtime environment.
#   - PATH prepends the venv so the `percival-deep-research` console
#     script is directly executable.
#   - VIRTUAL_ENV tells uv-based tooling where the venv lives.
#   - MCP_TRANSPORT=stdio is the default for MCP client compatibility
#     (Nanobot, OpenCode, Docker MCP gateway all speak stdio). Operators
#     who want HTTP/SSE should override with `MCP_TRANSPORT=sse`.
#   - DOCKER_CONTAINER=true keeps backward-compat for code paths that
#     inspect it (no behavior change since the auto-switch to SSE was
#     removed — see tests/test_docker.py::TestServerNoAutoSwitch).
#   - PYTHONUNBUFFERED + PYTHONFAULTHANDLER ensure logs flush and
#     crashes produce a useful traceback in `docker logs`.
ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_TRANSPORT=stdio \
    DOCKER_CONTAINER=true \
    LOG_LEVEL=INFO \
    PORT=8000

# Document the SSE/streamable-http port. The Docker MCP gateway uses
# stdio and never publishes a port; HTTP transports do.
EXPOSE 8000

USER percival

# tini reaps zombies + forwards signals (SIGTERM → graceful shutdown).
# ENTRYPOINT exec form: signals reach the Python process directly.
ENTRYPOINT ["/usr/bin/tini", "--", "percival-deep-research"]
CMD []

# HEALTHCHECK only meaningful for SSE/streamable-http transports; in
# stdio mode no port is bound and the check will fail (marking the
# container "unhealthy"), which is informational — stdio servers are
# still functional. Operators using stdio can pass `--no-healthcheck`
# or `--health-cmd=none` to silence it.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 || exit 1
