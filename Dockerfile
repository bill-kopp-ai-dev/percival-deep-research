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
FROM python:3.12-slim@sha256:6b25cbe6577518889d553cdd5a5da97d259348d8f6e45b527dd731caaba27a07 AS python-runtime

FROM ghcr.io/astral-sh/uv:0.9.30-python3.12-trixie-slim@sha256:41eb228142f776ed8df9e51fba89ee31f018c04a0452645c014783546b164c03 AS builder

WORKDIR /app

# uv tuning — never download Python interpreters (we use the bundled one),
# and prefer `copy` link mode for predictable layer diffs. We deliberately
# leave `UV_COMPILE_BYTECODE` UNSET: with Python's `PYTHONDONTWRITEBYTECODE=1`
# in effect, uv respects that and produces zero `.pyc` files, which saves
# ~120 MB in the venv (the MCP server is long-running; one-time import cost
# is negligible compared to gpt-researcher's heavy module loads).
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

# Copy ONLY the metadata needed to resolve dependencies first, so source
# edits don't bust the dependency layer.
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install deps without installing the project itself (fast path).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --no-install-package nltk --frozen

# Now copy the full source tree and install the project (so the
# `percival-deep-research` console script is registered in the venv).
COPY . .

# Install this project as a package + apply the gpt-researcher patch.
# The patch is mandatory: without it, the runtime crashes at first
# import of gpt_researcher.actions.query_processing with
# `NameError: name 'Any' is not defined` on Python 3.11/3.12.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-package nltk --frozen \
    && uv run --no-sync python scripts/patch_gpt_researcher.py \
    && TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken uv run --no-sync python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

# Strip package bloat that is irrelevant to runtime (saves ~50 MB across
# the 223 installed packages):
#   - `tests/` and `test/` directories inside site-packages
#     (pytest discovery / fixture imports, never used at runtime);
#   - `*.pyi` type stubs (only consulted by mypy/pyright, not Python);
#   - `*.dist-info/RECORD` and `INSTALLER` files (pip uses these for
#     uninstall bookkeeping; the runtime uses importlib.metadata which
#     reads METADATA + entry_points, both of which we keep);
#   - `uv_cache.json` (build cache metadata that embeds timestamps and
#     therefore made two clean builds of the same SHA differ);
#   - the `ddgs` console script: both `ddgs` and the transitively installed
#     `duckduckgo-search` provide a script with that name, and which one
#     wins depends on install order — the only difference left between two
#     clean builds of the same SHA. The server never uses the CLI wrapper.
# `find ... -prune` skips any directory whose name starts with `_` or
# `.` to avoid removing private vendor subdirs (e.g. `_pytest`, `__pycache__`,
# though the latter is already empty thanks to PYTHONDONTWRITEBYTECODE).
RUN find /app/.venv \
        -type d \( -name 'tests' -o -name 'test' \) -prune -exec rm -rf {} + \
    && find /app/.venv -name '*.pyi' -delete \
    && find /app/.venv -name 'RECORD' -path '*.dist-info/RECORD' -delete \
    && find /app/.venv -name 'INSTALLER' -path '*.dist-info/INSTALLER' -delete \
    && find /app/.venv -name 'uv_cache.json' -delete \
    && rm -f /app/.venv/bin/ddgs

# Normalize file timestamps so two clean builds of the same source produce
# the same layer content (reproducibility). `SOURCE_DATE_EPOCH` must be
# provided by the build (CI passes the commit timestamp).
ARG SOURCE_DATE_EPOCH=0
RUN if [ "${SOURCE_DATE_EPOCH}" != "0" ]; then \
        find /app -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + ; \
    fi

# ──────────────────────────────────────────────────────────────────────
# Stage 2: runtime
# ──────────────────────────────────────────────────────────────────────
FROM debian:forky-slim@sha256:4cee6ff3ebc49e32d55a857e25164ef8e5f8fecff2a186c6393f7e8bd8c23b53 AS runtime

ARG SOURCE_DATE_EPOCH=0

# Copy the CPython runtime with an explicit `cp -a` instead of
# `COPY --from`. BuildKit stamps the destination directories of a
# `COPY --from` with the build time, so two clean builds of the same
# source produced different layer digests even with identical content.
RUN --mount=type=bind,from=python-runtime,source=/usr/local,target=/mnt/usr-local \
    cp -a /mnt/usr-local/. /usr/local/ \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12 \
              /usr/local/bin/easy_install \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
              /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
              /usr/local/lib/python3.12/site-packages/setuptools \
              /usr/local/lib/python3.12/site-packages/setuptools-*.dist-info \
              /usr/local/lib/python3.12/site-packages/_distutils_hack \
              /usr/local/lib/python3.12/ensurepip/_bundled \
    && if [ "${SOURCE_DATE_EPOCH}" != "0" ]; then \
           find /usr/local -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + ; \
       fi

ARG VERSION=0.0.0
ARG GIT_SHA=unknown
ARG GPT_RESEARCHER_VERSION=0.16.0

# OCI / MCP catalog metadata — queryable via `docker inspect` and
# required for the Docker MCP Catalog (hub.docker.com/mcp).
LABEL org.opencontainers.image.title="percival-deep-research" \
      org.opencontainers.image.description="Multi-source web research and report generation MCP server, optimized for the Nanobot agent ecosystem." \
      org.opencontainers.image.source="https://github.com/bill-kopp-ai-dev/percival-deep-research" \
      org.opencontainers.image.documentation="https://github.com/bill-kopp-ai-dev/percival-deep-research/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Positronic Bean Labs" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      io.percival.gpt-researcher.version="${GPT_RESEARCHER_VERSION}" \
      io.percival.gpt-researcher.patch="query-processing-future-annotations" \
      io.modelcontextprotocol.server.name="percival-deep-research"

# Runtime essentials.
#
# The image deliberately embeds no init: the launcher owns the init layer
# (``docker run --init`` / Compose ``init: true``). A tini embedded here plus
# the launcher's own init would stack two supervision layers, and the outer
# one masks which process is actually responsible for SIGTERM.
ARG DEBIAN_SNAPSHOT=20261020T000000Z
ARG SOURCE_DATE_EPOCH=0
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s forky main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s forky-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
          ca-certificates=20260816 \
          libssl3t64=3.6.5-1 libffi8=3.8.0-2 libsqlite3-0=3.53.4-2 \
          libreadline8t64=8.3-4 libncursesw6=6.6+20260608-2 libtinfo6=6.6+20260608-2 \
          libdb5.3t64=5.3.28+dfsg2-11+b1 libgdbm6t64=1.26-1+b2 \
          libbz2-1.0=1.0.8-6+b2 liblzma5=5.8.4-1 libuuid1=2.42.4-1 \
          libzstd1=1.5.7+dfsg-4 zlib1g=1:1.3.dfsg+really1.3.2-3 \
          libtk8.6=8.6.18-1 libtcl8.6=8.6.18+dfsg-1 \
    && ln -sf /usr/local/lib/libpython3.12.so.1.0 /usr/local/lib/libpython3.12.so \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python \
    && chmod u-s /usr/bin/mount \
    && rm -f /usr/bin/nsenter /usr/bin/infocmp \
    && find / -xdev -type f -perm /6000 -exec chmod a-s {} + \
    && rm -f /usr/bin/apt /usr/bin/apt-get /usr/bin/apt-cache /usr/bin/apt-config /usr/bin/apt-mark /usr/bin/apt-cdrom \
    && rm -rf /usr/lib/apt /etc/apt /var/cache/apt \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/log/apt /var/log/dpkg.log /var/cache/ldconfig/aux-cache \
    && if [ "${SOURCE_DATE_EPOCH}" != "0" ]; then \
           find / -xdev \
               \( -path /proc -o -path /sys -o -path /dev \
                  -o -path /etc/hosts -o -path /etc/resolv.conf -o -path /etc/hostname \) \
               -prune -o -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + ; \
       fi

# Non-root user (UID 1000 matches the convention used by HKUDS/nanobot).
#
# `useradd` records the current day in `/etc/shadow` and stamps the
# account files with the build time; both are normalized here so that two
# clean builds of the same source produce the same layer.
RUN groupadd --system --gid 1000 percival \
    && useradd  --system --uid 1000 --gid percival \
        --home-dir /app --shell /usr/sbin/nologin percival \
    && sed -i 's/^percival:[^:]*:[0-9]*:/percival:!:0:/' /etc/shadow \
    && mkdir -p /app/reports /app/logs /app/.cache \
    && chown -R percival:percival /app \
    && if [ "${SOURCE_DATE_EPOCH}" != "0" ]; then \
           find /etc /app \
               \( -path /etc/hosts -o -path /etc/resolv.conf -o -path /etc/hostname \) \
               -prune -o -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + ; \
       fi

WORKDIR /app

# Copy the prepared venv + project source from the builder.
#
# As with the CPython runtime, an explicit `cp -a` from a bind mount is
# used instead of `COPY --from`: BuildKit stamps the destination
# directory of a `COPY --from` with the build time, which made two clean
# builds of the same source produce different layer digests.
RUN --mount=type=bind,from=builder,source=/app,target=/mnt/app \
    cp -a /mnt/app/. /app/ \
    && chown -R percival:percival /app \
    && if [ "${SOURCE_DATE_EPOCH}" != "0" ]; then \
           find /app -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} + ; \
       fi

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
    TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken \
    LITELLM_LOCAL_MODEL_COST_MAP=true \
    MCP_TRANSPORT=stdio \
    DOCKER_CONTAINER=true \
    LOG_LEVEL=INFO \
    PORT=8000

# Document the SSE/streamable-http port. The Docker MCP gateway uses
# stdio and never publishes a port; HTTP transports do.
EXPOSE 8000

USER percival

# The init layer belongs to the launcher (``docker run --init`` / Compose
# ``init: true``), so this image must not embed a second one.
# ENTRYPOINT exec form: signals reach the Python process directly.
ENTRYPOINT ["percival-deep-research"]
CMD []
