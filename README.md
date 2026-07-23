# 🤖 Percival Deep Research - percival.OS MCP

**Version 2.2.0**

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival Deep Research** is a highly capable MCP server designed to equip the Nanobot agent with autonomous, deep-dive web research capabilities. It explores and validates numerous sources, focusing only on relevant, trusted, and up-to-date information.

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Privacy & Governance**: The entire research and synthesis process is governed by your API keys and local configurations.
- **Data Sovereignty**: Knowledge extracted from the web is processed locally and integrated into your agent's context without external harvesting.
- **Hardened Security**: We implement *Defense-in-depth* with strict input sanitization against prompt injection and isolation of untrusted web content.
- **Transparency**: Based on the `GPT Researcher` project, but extensively refactored and hardened for the Percival ecosystem.

---

## 🚀 Features & Tools

### Research Tools
- `research_deep(query)`: Start multi-source deep web research (30–120s). Returns a `research_id`.
- `research_quick_search(query)`: Fast raw snippet search via the configured `RETRIEVER` (default: DuckDuckGo, no API key; 3–10s).
- `research_write_report(research_id, custom_prompt?)`: Generates a structured Markdown report from an existing session.
- `research_get_sources(research_id)`: Returns title, URL, and content size for all sources consulted.
- `research_get_context(research_id)`: Returns the raw synthesized context text without generating a report.

### Resources
- `research://{topic}`: Access cached or live web research context for a topic directly as an MCP resource.

---

## ⚙️ Configuration in percival.OS (Nanobot)

### Quickstart (v2.2.0 — recommended)

The server now uses **a single inference endpoint** (one LLM) instead of
the four-slot configuration from v2.1.x. The same setup works for
**any** OpenAI-compatible gateway (OpenAI, Venice, MiniMax, OpenRouter,
local LLMs, etc.).

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
        "INFERENCE_BASE_URL": "https://api.venice.ai/api/v1",
        "INFERENCE_LLM": "venice:llama-3.3-70b",
        "RETRIEVER": "duckduckgo"
      },
      "tool_timeout": 300
    }
  }
}
```

### Migration from v2.1.x

If you were using the old four-slot setup, here's the diff:

```diff
- "OPENAI_API_KEY": "...",
- "OPENAI_BASE_URL": "https://api.venice.ai/api/v1",
- "FAST_LLM": "venice:llama-3.3-70b",
- "SMART_LLM": "...",
- "STRATEGIC_LLM": "...",
- "EMBEDDING_LLM": "...",
- "PERCIVAL_LLM_PROVIDER_ALIASES": "venice:,minimax:,openrouter:",
- "BRAVE_API_KEY": "...",
- "RETRIEVER": "brave"
+ "INFERENCE_API_KEY": "...",
+ "INFERENCE_BASE_URL": "https://api.venice.ai/api/v1",
+ "INFERENCE_LLM": "venice:llama-3.3-70b",
+ "RETRIEVER": "duckduckgo"   // (or "brave" + BRAVE_API_KEY if you really want it)
```

Old variables are still accepted as fallback (with a deprecation log),
so existing v2.1.x setups keep working until v3.0.

---

## ⚠️ Known Limitations (v2.2.x)

These are honest design constraints, not bug reports — we surface them
so operators know what to expect when targeting non-OpenAI gateways:

1. **Embeddings require an OpenAI-compatible provider.** When you set
   `INFERENCE_LLM=minimax:...` (or venice:, openrouter:, etc.) for chat
   synthesis, the embedding slot is left **unset** instead of receiving
   the chat model — `gpt-researcher/memory/embeddings.py` previously
   received whatever `INFERENCE_LLM` said, which silently produced
   garbage. If your non-OpenAI provider doesn't have a native embedding
   endpoint, you'll need to either:
   - Use `INFERENCE_LLM=openai:<text-embedding-model>` and a separate
     chat endpoint (advanced), or
   - Keep the chat model on OpenAI (`gpt-4o-mini`) and accept the small
     cost for embeddings, or
   - Accept that **embeddings will fall back to in-process heuristics**
     in this version. The system degrades gracefully (warns on first
     use) — it does not crash.

2. **The four-slot override is gone if you skip `INFERENCE_LLM`.** When
   you provide `STRATEGIC_LLM`/`FAST_LLM`/`SMART_LLM`/`EMBEDDING_LLM`
   but not `INFERENCE_LLM`, only the slots you explicitly set are
   honored. Older v2.0 / v2.1 setups that dropped `INFERENCE_LLM`
   entirely without filling each slot will run with **only the slots
   they set** — others remain unset, which `gpt-researcher` treats as a
   hard fail at first use. Workaround: set `INFERENCE_LLM=` to the
   chat-model you want everywhere.

3. **`gpt-researcher >= 0.16.0` upstream bug.** The vendored copy in
   `.venv` (after `uv sync`) hits `NameError: name 'Any' is not
   defined` at import time. We've applied a `from __future__ import
   annotations` patch in our local venv (see `scripts/patch_gpt_researcher.py`).
   Without it, the server never boots. If you destroy your venv,
   re-run `uv run python scripts/patch_gpt_researcher.py` after `uv sync`.

4. **DuckDuckGo retriever rate-limits on heavy traffic.** DuckDuckGo
   doesn't publish rate limits but returns `HTTP 429` after sustained
   scraping. Operators chaining large batched research should consider
   Brave (with `BRAVE_API_KEY`) or a local SearXNG instance.

---

## 🛠️ Development & Testing
This project uses the `uv` for dependency management within the unified `percival.OS_Dev` environment.

```bash
cd percival.OS_Dev
uv sync
uv run percival-deep-research
```

---

## 🛟 Troubleshooting (v2.2.x)

These cover the 9 bugs identified in [the Nano report of 2026-07-23](../MCP_Docs/Issues/2026-07-23-percival-deep-research-shipping-bugs.md). If a symptom matches, the fix is below.

### "401 Incorrect API key" on custom gateway (e.g. Venice, MiniMax)

**Cause:** `gpt-researcher/memory/embeddings.py` (upstream, not editable)
reads `os.environ["OPENAI_BASE_URL"]` / `os.environ["OPENAI_API_KEY"]`
directly. Setting only `INFERENCE_BASE_URL` / `INFERENCE_API_KEY` is
insufficient — v2.2.1 added a **bridge in `populate_inference_slots()`** that
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

If it says `openai`, your `INFERENCE_BASE_URL` is wrong (must contain the
gateway host — `api.venice.ai`, `api.minimax.io`, `openrouter.ai`).

### "EMBEDDING_LLM = gpt-4o-mini" — bad embedding model

**Cause:** `INFERENCE_LLM` value was being copied 1-for-1 into
`EMBEDDING_LLM`, which silently produces garbage embeddings. v2.2.1
fixes this: embeddings slot now gets a sensible default
(`openai:text-embedding-3-small`) only when the provider is
OpenAI-compatible. For non-OpenAI providers (minimax:, venice:), it is
**left unset** so `gpt-researcher` falls back to its in-process
heuristic rather than generating garbage.

If you need embeddings on a non-OpenAI provider, override:
```env
INFERENCE_LLM=minimax:MiniMax-M3
EMBEDDING_LLM=<your-provider's-embedding-model>
```

### `pytest -q` reports `1 failed` instead of green

**Cause (B4):** integration tests connect to `localhost:8000` and fail
if no server is up. v2.2.1 adds an `autouse` fixture in
`tests/conftest.py` that **skips** integration tests without a server:

```
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

### `__version__` reports `2.1.0` instead of `2.2.x`

**Cause (B6):** the editable install hasn't been refreshed since the
version bump. Re-install:
```bash
uv pip install -e . --force-reinstall
# OR
uv sync
```

The new regression test `tests/test_audit_round3_nano.py::test_version_correto_no_runtime`
will fail loudly on any future drift.

### Resource `research://topic with space` fails with `invalid domain character`

**Cause:** FastMCP 3.4 Pydantic validator rejects non-ASCII in URI
domains. v2.2.0 added percent-decode **server-side**, so callers can
either:

```python
# Option A: percent-encode the topic (recommended)
await client.read_resource("research://S%C3%A3o%20Paulo")

# Option B: encode at the call site
import urllib.parse
uri = "research://" + urllib.parse.quote("São Paulo", safe="")
await client.read_resource(uri)
```

Option A is preferred — it's also what FastMCP's own client does
automatically. v2.2.1 includes the fix on the server side.

### `prompts/list` shows `description='...'`

**Cause (B7):** some `"""..."""` docstrings were placeholders. They've
been replaced in v2.2.1. If you still see this in a fork, replace with
a real docstring (parseable by `prompts/list`).

### `Component already exists: template:research://{topic}` at boot (B8)

**Cause:** the resource template `research://{topic}` was registered
twice during boot. Two triggers known in FastMCP 3.4:

1. Running server.py with `python -i server.py` (interactive mode
   imports modules twice).
2. Subprocess imports the package via `importlib.reload()`.

The v2.2.1 regression test
`tests/test_audit_round3_nano.py::test_apenas_um_template_research_topic`
will catch this and prevent regression.

---

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It enables Nanobot to perform complex research tasks that require multiple steps of validation and synthesis.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
