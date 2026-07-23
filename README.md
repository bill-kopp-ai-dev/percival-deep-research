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

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It enables Nanobot to perform complex research tasks that require multiple steps of validation and synthesis.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
