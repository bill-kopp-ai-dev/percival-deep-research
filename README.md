# 🤖 Percival Deep Research — percival.OS MCP

**Version 3.0.1** · [CHANGELOG](CHANGELOG.md) · [percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-411%20passed-blue.svg)]()

Multi-source web research and report generation, exposed as an MCP server
for the [Nanobot](https://github.com/HKUDS/nanobot) agent ecosystem. Also
compatible with [OpenCode](https://github.com/anomalyco/opencode),
[Claude Desktop](https://claude.ai/download), the
[Docker MCP Toolkit / Catalog](https://docs.docker.com/ai/mcp-catalog-and-toolkit/),
and any generic MCP client.

## ✨ Highlights

- **5 tools + 1 resource template + 4 prompts** — covers the full research
  workflow (deep dive → quick lookup → follow-up reads → long-form report).
- **Single-endpoint inference** — one LLM (`INFERENCE_LLM`) for all tasks;
  works with OpenAI, Venice, MiniMax, OpenRouter, and any OpenAI-compatible
  gateway.
- **Defense-in-depth hardening** — input sanitization against prompt
  injection, `[SECURITY WARNING:...]` wrapping of untrusted web content,
  strict-bool validation at the framework layer.
- **Docker-ready** — multi-stage image (`~1.37 GB`), non-root, stdio by
  default, OCI/MCP labels for catalog submission.
- **Battle-tested** — 411 tests passing (zero integration deps needed); 48
  bugs closed across 4 official bug-hunt rounds + 2 internal reviews.

## 📑 Table of Contents

- [Description](#-description)
- [percival.OS Principles](#-percivalos-principles)
- [Surface](#-surface-v301)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Docker Deployment](#-docker-deployment)
- [Architecture](#-architecture)
- [Known Limitations](#-known-limitations-v301)
- [Development & Testing](#-development--testing)
- [Troubleshooting](#-troubleshooting-v301)
- [About the Project](#-about-the-project)
- [Versioning](#-versioning)
- [Acknowledgements](#-acknowledgements)

---

## 📋 Description

**Percival Deep Research** is a highly capable MCP server designed to equip
the Nanobot agent with autonomous, deep-dive web research capabilities. It
explores and validates numerous sources, focusing only on relevant, trusted,
and up-to-date information.

This server is part of the **percival.OS** ecosystem, a Personal Agentic
Operating System designed for autonomy, security, and absolute privacy.

> **v3.0.1 highlights** — 48 bugs closed across 4 official bug-hunt rounds
> + 2 internal code-reviews; surface expanded to **5 tools + 1 resource
> template + 4 prompts**. New in v3.0.1: **Docker encapsulation**
> (multi-stage image, stdio default, Docker MCP Toolkit catalog metadata),
> **lint pass** (161 → 0 ruff errors), and **image shrink** (1.7 GB →
> 1.37 GB, –19.4%). See [CHANGELOG.md](CHANGELOG.md) for the full history.

---

## 🛡️ percival.OS Principles

Like all components of `percival.OS`, this MCP server strictly follows our
core principles:

- **Privacy & Governance** — the entire research and synthesis process is
  governed by your API keys and local configurations; no telemetry leaves
  your machine.
- **Data Sovereignty** — knowledge extracted from the web is processed
  locally and integrated into your agent's context without external
  harvesting.
- **Hardened Security** — *defense-in-depth* with strict input sanitization
  against prompt injection, isolation of untrusted web content (XML
  envelope / `[SECURITY WARNING:...]` prefix), and framework-level
  strict-bool validation.
- **Transparency** — based on the `gpt-researcher` project, but extensively
  refactored and hardened for the Percival ecosystem.

---

## 🚀 Surface (v3.0.1)

### Tools (5)

| Name | Function | Signature | Latency | Notes |
|---|---|---|---|---|
| `research_deep` | Multi-source deep research | `(query, include_context: StrictBool=False) → str` | 30–120 s | Rate-limited; in-flight dedup; returns `research_id` |
| `research_quick_search` | Raw snippets, no LLM synthesis | `(query) → str` | 3–10 s | Rate-limited; no synthesis |
| `research_get_context` | Wrapped research context | `(research_id) → str` | <1 s | `[SECURITY WARNING:…]` prefix |
| `research_get_sources` | Wrapped source metadata | `(research_id) → str` | <1 s | `[SECURITY WARNING:…]` prefix |
| `research_write_report` | Final markdown report | `(research_id, custom_prompt=None) → str` | 5–30 s | LLM-free when `custom_prompt=None` |

### Resource (1)

- `research://{topic}` — direct context lookup (no session). Percent-decoded
  server-side (so callers may use either `research://São Paulo` or
  `research://S%C3%A3o%20Paulo`).

### Prompts (4)

| Prompt | When to use |
|---|---|
| `research_query(topic, goal?, report_format?)` | Full workflow (deep + report) |
| `research_quick_brief(topic)` | Raw snippets without synthesis (shortcut, no LLM) |
| `research_synthesis(research_id, audience?, length?)` | Re-format existing research by audience (`general` / `executive` / `technical` / `academic`) |
| `research_health_diagnose(symptoms)` | Error triage via `/health` + `/metrics` (decision tree: retry / rephrase / escalate / report) |

---

## 📦 Installation

### Prerequisites

- **Python ≥ 3.11** (tested on 3.11 and 3.12)
- **uv** ([install instructions](https://docs.astral.sh/uv/getting-started/installation/))
- For Docker: **Docker Engine ≥ 23** (BuildKit enabled by default)
- An **inference API key** (OpenAI, Venice, MiniMax, OpenRouter, or any
  OpenAI-compatible endpoint)

### Install from source

```bash
git clone https://github.com/bill-kopp-ai-dev/percival.OS.git
cd percival.OS/percival-deep-research   # this directory

uv sync                                  # installs deps + applies gpt-researcher patch
uv run percival-deep-research            # boots in stdio mode
```

> **Note**: this server lives in the `percival-deep-research/` subdirectory
> of the `percival.OS` monorepo. All commands below assume you're inside
> that directory.

### Pre-built Docker image

```bash
docker build -t percival-deep-research:local .
```

See [Docker Deployment](#-docker-deployment) for full instructions.

### Install as a tool (optional)

```bash
uv tool install --from . percival-deep-research
percival-deep-research --help        # verify install
```

---

## ⚙️ Configuration

All configuration is via environment variables. See
[`.env.example`](.env.example) for the full template.

### Required

| Variable | Purpose |
|---|---|
| `INFERENCE_API_KEY` | API key for the inference endpoint |

### Single-endpoint inference (v3.0+)

| Variable | Default | Purpose |
|---|---|---|
| `INFERENCE_LLM` | `openai:gpt-4o-mini` | `provider:model` format — provider is auto-detected from `INFERENCE_BASE_URL` host |
| `INFERENCE_BASE_URL` | (auto) | OpenAI-compatible URL; `venice:`/`minimax:`/`openrouter:` aliases are auto-detected |

### Retriever (web search backend)

| Variable | Default | Purpose |
|---|---|---|
| `RETRIEVER` | `duckduckgo` | `duckduckgo` (no API key) or `brave` (needs `BRAVE_API_KEY`) |
| `BRAVE_API_KEY` | — | Required only if `RETRIEVER=brave` |

### Transport

| Variable | Default | Purpose |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` (Nanobot / OpenCode / gateway), `sse` (HTTP), or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | Bind address for HTTP; container services override to `0.0.0.0` internally |
| `PORT` | `8000` | Bind port for HTTP transports |

### Tuning

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Standard log levels |
| `PERCIVAL_RESEARCH_TIMEOUT_S` | `90` | Max seconds for one research |
| `PERCIVAL_MAX_CONCURRENT_RESEARCH` | `3` | Concurrent in-flight researches |

### Migration from v2.x

```diff
- "OPENAI_API_KEY": "...",
- "OPENAI_BASE_URL": "https://api.venice.ai/api/v1",
- "FAST_LLM": "...",
- "SMART_LLM": "...",
- "STRATEGIC_LLM": "...",
- "EMBEDDING_LLM": "...",
- "PERCIVAL_LLM_PROVIDER_ALIASES": "venice:,minimax:,openrouter:",
- "BRAVE_API_KEY": "...",
+ "INFERENCE_API_KEY": "...",
+ "INFERENCE_BASE_URL": "...",
+ "INFERENCE_LLM": "<provider>:<model>",
+ "RETRIEVER": "duckduckgo"   // or "brave" + BRAVE_API_KEY
```

**Breaking changes v2.x → v3.0:**

- ❌ `OPENAI_*` env vars (still accepted as fallback with deprecation log;
  will be removed in v4.0).
- ❌ `FAST_LLM`/`SMART_LLM`/`STRATEGIC_LLM`/`EMBEDDING_LLM` per-slot
  overrides (still honored when set, but `INFERENCE_LLM` is canonical).
- ❌ Llm-bridge expansion `venice:`, `minimax:`, `openrouter:` (now
  auto-detected from `INFERENCE_BASE_URL`).
- ❌ `BRAVE_API_KEY` is needed only if `RETRIEVER=brave`.
- ✅ v3.0 NEW: `research_quick_brief`, `research_synthesis`,
  `research_health_diagnose` prompts.
- ✅ v3.0 NEW: strict validation on `deep_research(include_context)` —
  accepts only real `bool`. `'yes'`/`'false'`/`1` are rejected at the
  framework level (Pydantic StrictBool in the type annotation).

> **⚠️ Use literals** — `INFERENCE_LLM=${INFERENCE_LLM:-default}` and
> similar bash-style placeholders are **not interpolated**. v3.0 detects
> this and emits WARN [S6], but the pipeline breaks silently if you don't
> fix it. Always copy the value directly:
> `INFERENCE_LLM=openai:gpt-4o-mini`.

---

## 🚀 Usage

The server speaks **stdio by default**, which is the canonical MCP
transport. Below are the three most common ways to wire it up.

### With Nanobot (or any MCP client via `command`/`args`)

Add to `~/.nanobot/config.json` (or via the WebUI **Apps** tab):

```json
{
  "mcpServers": {
    "percival-deep-research": {
      "command": "uv",
      "args": ["run", "--no-sync", "percival-deep-research"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_TRANSPORT": "stdio",
        "INFERENCE_API_KEY": "YOUR_KEY",
        "INFERENCE_BASE_URL": "https://api.openai.com/v1",
        "INFERENCE_LLM": "openai:gpt-4o-mini",
        "RETRIEVER": "duckduckgo"
      },
      "tool_timeout": 300
    }
  }
}
```

### With OpenCode

Add to `.opencode/mcp.json` (project) or `~/.config/opencode/mcp.json`
(global):

```json
{
  "mcp": {
    "percival-deep-research": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--no-sync", "percival-deep-research"],
      "env": {
        "INFERENCE_API_KEY": "YOUR_KEY",
        "INFERENCE_LLM": "openai:gpt-4o-mini"
      }
    }
  }
}
```

### With the Docker MCP Toolkit / Catalog

After building the image (`docker build -t percival-deep-research:local .`):

```bash
docker mcp catalog import ./docker/
docker mcp gateway run --profile my_profile
```

The catalog metadata (`docker/server.yaml` + `docker/tools.json` +
`docker/README.md`) declares the server as `mcp/percival-deep-research`
with `INFERENCE_API_KEY` and `BRAVE_API_KEY` as secrets. See
[Docker Deployment](#-docker-deployment) for full integration recipes.

### Programmatic (Python MCP client)

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("uv://run?percival-deep-research") as client:
        tools = await client.list_tools()
        result = await client.call_tool(
            "research_deep",
            {"query": "what is the capital of France?"},
        )
        print(result)

asyncio.run(main())
```

---

## 🐳 Docker Deployment

The server ships as a multi-stage Docker image compatible with **Nanobot**,
**OpenCode**, the **Docker MCP Toolkit / Catalog**, Claude Desktop, and any
generic MCP client. The container speaks **stdio by default**; HTTP/SSE is
opt-in via env.

### Quickstart — `docker run` (stdio)

```bash
docker run -i --rm \
  -e INFERENCE_API_KEY=<your-key> \
  -e INFERENCE_LLM=openai:gpt-4o-mini \
  percival-deep-research:local
```

`-i` keeps stdin open so the container can receive JSON-RPC over stdio.
This is the canonical invocation for MCP clients that spawn the server as a
subprocess.

### Quickstart — `docker run` (HTTP/SSE)

```bash
docker run -d --rm -p 127.0.0.1:8000:8000 \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e INFERENCE_API_KEY=<your-key> \
  -e INFERENCE_LLM=openai:gpt-4o-mini \
  percival-deep-research:local
```

Browse `http://127.0.0.1:8000/health` to confirm the boot status.

### Docker Compose

```bash
# Stdio (one-shot; no TTY, published port, healthcheck, or restart policy):
docker compose run --rm -T percival-deep-research-stdio

# HTTP/SSE (opt-in; host loopback by default):
HTTP_PORT=8765 docker compose --profile http up -d percival-deep-research-http

# Production stack with nginx reverse proxy (requires reviewed ./nginx.conf):
docker compose --profile production up -d
```

Stdio and HTTP use separate Compose services. Both mount `./logs` and
`./reports` for persistence and read secrets from an optional local `.env`.
The HTTP profile publishes only on `127.0.0.1` by default; do not expose this
unauthenticated HTTP service directly to an untrusted network.
The `production` profile bind-mounts `./nginx.conf`; supply and review that
proxy configuration before starting the profile.

### Integration with MCP clients

**Nanobot via Docker** — add to `~/.nanobot/config.json`:

```json
{
  "mcpServers": {
    "percival-deep-research": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "INFERENCE_API_KEY",
        "-e", "INFERENCE_LLM=openai:gpt-4o-mini",
        "-e", "MCP_TRANSPORT=stdio",
        "percival-deep-research:local"
      ],
      "env": {
        "INFERENCE_API_KEY": "YOUR_KEY"
      }
    }
  }
}
```

**OpenCode via Docker** — add to `.opencode/mcp.json`:

```json
{
  "mcp": {
    "percival-deep-research": {
      "type": "stdio",
      "command": [
        "docker", "run", "-i", "--rm",
        "-e", "INFERENCE_API_KEY",
        "-e", "INFERENCE_LLM=openai:gpt-4o-mini",
        "-e", "MCP_TRANSPORT=stdio",
        "percival-deep-research:local"
      ],
      "env": {
        "INFERENCE_API_KEY": "YOUR_KEY"
      }
    }
  }
}
```

**Docker MCP Toolkit / Catalog** — the image is annotated with the
required OCI + MCP labels (`io.modelcontextprotocol.server.name=
percival-deep-research`) and ships the catalog metadata under
`docker/server.yaml` + `docker/tools.json` + `docker/README.md`. To
publish to the public catalog (hub.docker.com/mcp), PR those files into
[`docker/mcp-registry`](https://github.com/docker/mcp-registry) under
`servers/percival-deep-research/`.

### Smoke test

A scripted end-to-end test that boots the image in both transports and
verifies the JSON-RPC initialize roundtrip + `/health` endpoint:

```bash
bash scripts/docker_smoke_test.sh
```

Build takes ~30 s on a warm cache; the full run takes ~45 s including
the SSE boot.

### Image details

| | |
|---|---|
| Base | `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` (builder) → `python:3.11-slim` (runtime) |
| Size | ~1.37 GB (pulls the full `gpt-researcher` + ML deps stack; venv bloat stripped — `tests/`, `*.pyi`, `*.dist-info/RECORD`, no `.pyc` files) |
| User | non-root `percival` (UID 1000) |
| Signal | PID 1 = `tini` → forwards SIGTERM to the MCP server |
| Default transport | `stdio` |
| Health endpoint | `GET /health` (200 healthy / 503 degraded) — only meaningful in HTTP mode |

---

## 🏗️ Architecture

The server sits between an MCP client (Nanobot, OpenCode, Claude Desktop,
the Docker MCP gateway, or any stdio consumer) and `gpt-researcher`, which
in turn drives the configured inference endpoint and retriever:

```
MCP client ──stdio/HTTP──▶ FastMCP app ──▶ gpt-researcher
                                │                  │
                                │                  ├──▶ OpenAI-compatible LLM (chat + summary)
                                │                  └──▶ DuckDuckGo / Brave / SearXNG (retrieval)
                                │
                                ├──▶ research_limiter (rate-limit / dedup)
                                ├──▶ registry (active sessions + cached results)
                                ├──▶ metrics (Prometheus-style counters)
                                ├──▶ /health + /metrics custom routes
                                └──▶ @mcp.tool decorators expose the 5 public tools
```

**Security boundary** — untrusted web content (returned by `research_get_*`)
is wrapped with a `[SECURITY WARNING:...]` prefix so the calling agent
treats it as data, not instruction. The XML envelope is applied at the
`utils.py` level for the `research://{topic}` resource. Input sanitization
lives in `sanitize_query()` / `sanitize_topic()` (utils.py).

**Determinism guarantees** — `StrictBool` on `include_context` is enforced
at the Pydantic layer (FastMCP 3.4+) before our handler runs, so a v2.x
agent that passed `'yes'` fails fast with a clear `ToolError` instead of
silently being coerced.

**Single-endpoint inference** — `INFERENCE_LLM` drives chat, summary, and
strategy. `populate_inference_slots()` (`llm_bridge.py`) propagates the
canonical `INFERENCE_*` env vars to the legacy `OPENAI_*` namespace that
`gpt-researcher/memory/embeddings.py` reads directly — this is the only
way to make non-OpenAI gateways (Venice, MiniMax, OpenRouter, local LLMs)
work end-to-end without forking the upstream.

---

## ⚠️ Known Limitations (v3.0.1)

These are honest design constraints, not bug reports:

1. **Embeddings require an OpenAI-compatible provider.** When you set
   `INFERENCE_LLM=minimax:...` (or venice:, openrouter:, etc.) for chat
   synthesis, the embedding slot is left **unset** instead of receiving
   the chat model — `gpt-researcher/memory/embeddings.py` previously
   received whatever `INFERENCE_LLM` said, which silently produced
   garbage. See troubleshooting below.

2. **The four-slot override is gone if you skip `INFERENCE_LLM`.** When
   you provide `STRATEGIC_LLM`/`FAST_LLM`/`SMART_LLM`/`EMBEDDING_LLM`
   but not `INFERENCE_LLM`, only the slots you explicitly set are
   honored. Workaround: set `INFERENCE_LLM=` to the chat-model you want
   everywhere.

3. **`gpt-researcher >= 0.16.0` upstream bug.** The vendored copy in
   `.venv` (after `uv sync`) hits `NameError: name 'Any' is not
   defined` at import time. We've applied a `from __future__ import
   annotations` patch in our local venv (see `scripts/patch_gpt_researcher.py`).
   Without it, the server never boots. If you destroy your venv,
   re-run `uv run python scripts/patch_gpt_researcher.py` after `uv sync`.
   The Docker image runs the patch inside its build stage automatically.

4. **DuckDuckGo retriever rate-limits on heavy traffic.** DuckDuckGo
   doesn't publish rate limits but returns `HTTP 429` after sustained
   scraping. Operators chaining large batched research should consider
   Brave (with `BRAVE_API_KEY`) or a local SearXNG instance.

5. **`include_context` schema strictness (v3.0+).** `Pydantic StrictBool`
   rejects `'yes'`, `'false'`, `1`, `0`, `dict`, etc. at the framework
   layer before the handler runs. Agents that previously passed
   `'yes'`/`'false'` will see a `ToolError`. Fix: pass real `True`/`False`.

---

## 🛠️ Development & Testing

```bash
# Inside the percival-deep-research/ directory of the monorepo:
uv sync
uv run percival-deep-research
```

### Test runs

```bash
# Whole suite (411 passed + 4 skipped; no integration deps needed).
uv run pytest -q

# Just the regression tests for placeholder detection / dedup / bloat.
uv run pytest tests/test_audit_round4_nano.py tests/test_audit_round5_placeholder.py -v

# Docker packaging regressions (Dockerfile, .dockerignore, server.py, catalog metadata).
uv run pytest tests/test_docker.py -v

# Smoke test (boots, version prints):
INFERENCE_API_KEY=sk-fake INFERENCE_BASE_URL=https://api.openai.com/v1 \
  INFERENCE_LLM=openai:gpt-4o-mini \
  timeout 4 uv run --no-sync percival-deep-research

# Docker end-to-end smoke (build + stdio JSON-RPC + HTTP/SSE /health):
bash scripts/docker_smoke_test.sh
```

---

## 🛟 Troubleshooting (v3.0.1)

### Stdio container has no Docker health status

Stdio has no HTTP healthcheck: Docker process liveness cannot prove MCP
protocol readiness. Validate it with `initialize` and `tools/list` through
the MCP client or `scripts/docker_smoke_test.sh`.

The HTTP profile probes `GET /health`. Its `healthy`/`degraded` body reports
configuration readiness; both HTTP 200 and 503 prove the endpoint is serving,
so a missing upstream credential is not misreported as a dead process.

```bash
HTTP_PORT=8765 docker compose --profile http up -d percival-deep-research-http
```

### HTTP port is already allocated

Choose another host port. The container continues listening on port 8000:

```bash
HTTP_PORT=8765 docker compose --profile http up -d percival-deep-research-http
# or for docker run (bind to loopback):
docker run -p 127.0.0.1:8765:8000 -e MCP_TRANSPORT=sse ...
```

### `docker build` fails with `NameError: name 'Any' is not defined`

Means `scripts/patch_gpt_researcher.py` did not run inside the build.
Verify the builder stage contains the `uv run --no-sync python
scripts/patch_gpt_researcher.py` line. If you're on `gpt-researcher <
0.16.0`, the patch is a no-op (idempotent) and you should NOT see this
error.

### Nanobot / OpenCode can't see the server after `docker compose run`

Common causes:
- `MCP_TRANSPORT` was set to `sse` somewhere (e.g. shell env) — stdio
  mode requires `MCP_TRANSPORT=stdio` explicitly when an env var
  shadows the Dockerfile default.
- The `command` in `mcp.json` doesn't match the image name. Confirm
  `docker images | grep percival-deep-research` shows your tag.
- The MCP client doesn't ship stdin over the `docker run -i` pipe —
  verify with `docker run --rm -i <image> < /dev/null` returns cleanly.

### `Error: Unsupported ${INFERENCE_LLM.` (N0)

**Cause:** Your `.env` or `config.json` contains a bash-style placeholder
template (`${VAR}` or `${VAR:-default}`) that the loader could not
interpolate. The literal string then hits `gpt_researcher.config.config.
parse_llm` and produces a cryptic `Unsupported ${INFERENCE_LLM.`.

**v3.0 detection:** If this happens, you'll also see this WARN at boot:

```
[S6] INFERENCE_LLM='${INFERENCE_LLM:-openai:gpt-4o-mini}' looks like an
UN-EXPANDED template placeholder. Most likely cause: `.env` or
`config.json` referenced a placeholder that the loader couldn't
interpolate.
```

**Fix:**

```diff
- INFERENCE_LLM=${INFERENCE_LLM:-openai:gpt-4o-mini}
+ INFERENCE_LLM=openai:gpt-4o-mini
```

Or in `config.json`:

```diff
- "INFERENCE_LLM": "${INFERENCE_LLM:-openai:gpt-4o-mini}"
+ "INFERENCE_LLM": "openai:gpt-4o-mini"
```

> The same WARN [S6] fires on missing `:` in the value (e.g.,
> `INFERENCE_LLM=gpt-4o-mini`) and on python-format `%(...)s` and on
> f-string `{...}` templates — all of these fail `parse_llm` the same
> way. The WARN points you to the exact file (`.env` or `config.json`).

### "401 Incorrect API key" on custom gateway (B3, e.g. Venice, MiniMax)

**Cause:** `gpt-researcher/memory/embeddings.py` (upstream, not editable)
reads `os.environ["OPENAI_BASE_URL"]` / `os.environ["OPENAI_API_KEY"]`
directly. Setting only `INFERENCE_BASE_URL` / `INFERENCE_API_KEY` is
insufficient — `populate_inference_slots()` in `llm_bridge.py`
propagates these env vars to the legacy `OPENAI_*` namespace. To use on
custom gateway:

```env
INFERENCE_API_KEY=sk-your-gateway-key
INFERENCE_BASE_URL=https://api.venice.ai/api/v1
INFERENCE_LLM=venice:llama-3.3-70b
```

After startup, log line should show:

```
Inference provider: venice (auto-detected from INFERENCE_BASE_URL)
```

If it says `openai`, your `INFERENCE_BASE_URL` is wrong (must contain
the gateway host — `api.venice.ai`, `api.minimax.io`, `openrouter.ai`).

### `pytest -q` reports failures on a clean machine (B4)

Integration tests connect to `localhost:8000` and fail if no server is
up. v2.2.1+ adds an `autouse` fixture in `tests/conftest.py` that
**skips** integration tests without a server:

```bash
uv run pytest -q
# Expected (v2.2.1+): N passed, M skipped
```

If you need to run them, start a server first:
```bash
# In one terminal:
MCP_TRANSPORT=sse uv run --no-sync percival-deep-research
# Then in another:
uv run pytest
```

### `__version__` reports the wrong number

Re-install the editable package:

```bash
uv pip install -e . --force-reinstall
# OR
uv sync
```

The regression test
`tests/test_audit_round3_nano.py::test_version_correto_no_runtime` will
fail loudly on any future drift.

### `research://topic with space` fails with `invalid domain character`

FastMCP 3.4 Pydantic validator rejects non-ASCII in URI domains. v2.2.0+
added percent-decode **server-side**, so callers can either:

```python
# Option A: percent-encode the topic (recommended)
await client.read_resource("research://S%C3%A3o%20Paulo")

# Option B: encode at the call site
import urllib.parse

uri = "research://" + urllib.parse.quote("São Paulo", safe="")
await client.read_resource(uri)
```

### `include_context='yes'` returns `ToolError` (N8/N9)

This was v2.x lax-mode accepting string-coerced bool, v3.0+ enforces
strict bool. Pass real `True`/`False`:

```python
# Wrong (was accepted in <v3.0):
await client.call_tool("research_deep", {"query": "x", "include_context": "yes"})

# Right:
await client.call_tool("research_deep", {"query": "x", "include_context": True})
```

Affected: `'yes'`, `'false'`, `1`, `0`, `{}` and similar truthy/falsy
non-bools. The framework (Pydantic StrictBool) now rejects these with
a clear ToolError before our handler runs.

### Spurious `Future exception was never retrieved` in server logs

Fixed in v3.0 (S3 fix): `deep_research` rate-limit-reject branch now
calls `future.exception()` to consume the exception cleanly. If you
still see this on a fork, ensure the in-flight dedup path consumes the
exception:

```python
if not future.done():
    future.set_exception(RuntimeError("..."))
future.exception()  # <- this line cleans the warning
```

### `Component already exists: template:research://{topic}` at boot

Two triggers known in FastMCP 3.4:
1. Running `server.py` with `python -i server.py` (interactive mode
   imports modules twice).
2. Subprocess imports the package via `importlib.reload()`.

The regression test
`tests/test_audit_round3_nano.py::test_apenas_um_template_research_topic`
catches this.

### Boot emits `[S6]` WARN even though `INFERENCE_LLM` looks valid

Possible causes (after v3.0 review):
- A stray `}` character somewhere (e.g., `model-v2}typo`). v3.0
  removed `}` as a false-positive signal, so this should not trigger
  anymore. If still triggered, file a bug.
- A leftover `gpt-{name}` template. v3.0 retains `{` as a placeholder
  signal — replace with literal values.

---

## 📚 About the Project

This server is an integral module of the **percival.OS** project — a
Personal Agentic Operating System designed for autonomy, security, and
absolute privacy. It equips the Nanobot agent (and any other MCP client)
with multi-step research capabilities that require validation and
synthesis across numerous sources.

- **percival.OS monorepo**: [github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **This server's directory**: `percival.OS/percival-deep-research/`
- **Issues**: [github.com/bill-kopp-ai-dev/percival.OS/issues](https://github.com/bill-kopp-ai-dev/percival.OS/issues)
- **License**: [MIT](LICENSE)

---

## 📝 Versioning

| Version | Status | Notes |
|---|---|---|
| 3.0.1 | ✅ current | Docker encapsulation (multi-stage image, stdio default, MCP catalog metadata); lint pass (161 → 0); image shrink (1.7 GB → 1.37 GB) |
| 3.0.0 | 🟠 superseded | 4 new prompts; strict-bool on `include_context`; INFERENCE_LLM placeholder detector |
| 2.3.x | 🟠 superseded | last with `include_context='yes'` accepted |
| 2.2.x | 🟠 superseded | single-endpoint inference introduced |
| 2.1.x | 🟢 legacy | four-slot `FAST_LLM`/`SMART_LLM`/… model |
| 1.0.x | 🟢 legacy | initial release |

See [CHANGELOG.md](CHANGELOG.md) for the complete history.

---

## 🙏 Acknowledgements

- [`HKUDS/nanobot`](https://github.com/HKUDS/nanobot) — the consumer
  agent this server is optimized for.
- [`assafelovic/gpt-researcher`](https://github.com/assafelovic/gpt-researcher)
  — upstream research engine; locally patched for Python 3.11/3.12 compat.
- [`jlowin/fastmcp`](https://github.com/jlowin/fastmcp) and the broader
  [MCP ecosystem](https://modelcontextprotocol.io/).

---

*Developed with ❤️ by the percival.OS Team*
