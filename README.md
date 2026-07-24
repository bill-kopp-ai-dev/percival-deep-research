# 🤖 Percival Deep Research - percival.OS MCP

**Version 3.0.0**

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival Deep Research** is a highly capable MCP server designed to equip the Nanobot agent with autonomous, deep-dive web research capabilities. It explores and validates numerous sources, focusing only on relevant, trusted, and up-to-date information.

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

> **v3.0 highlights** — 48 bugs closed across 4 official bug-hunt rounds and 2 internal code-reviews; surface expanded to **5 tools + 1 resource template + 4 prompts**. Same single-endpoint inference model as v2.2.x. See [CHANGELOG.md](CHANGELOG.md) for the full history.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Privacy & Governance**: The entire research and synthesis process is governed by your API keys and local configurations.
- **Data Sovereignty**: Knowledge extracted from the web is processed locally and integrated into your agent's context without external harvesting.
- **Hardened Security**: We implement *Defense-in-depth* with strict input sanitization against prompt injection and isolation of untrusted web content.
- **Transparency**: Based on the `GPT Researcher` project, but extensively refactored and hardened for the Percival ecosystem.

---

## 🚀 Surface (v3.0.0)

### Tools (5)

| Nome | Função | Assinatura | Latência | Notas |
|---|---|---|---|---|
| `research_deep` | Pesquisa profunda multi-source | `(query, include_context: StrictBool=False) → str` | 30–120 s | Rate-limited; in-flight dedup; retorna `research_id` |
| `research_quick_search` | Raw snippets, sem LLM | `(query) → str` | 3–10 s | Rate-limited; sem synthesis |
| `research_get_context` | Contexto crudo wrappado | `(research_id) → str` | <1 s | `[SECURITY WARNING:…]` prefixo |
| `research_get_sources` | Metadados das fontes wrappados | `(research_id) → str` | <1 s | `[SECURITY WARNING:…]` prefixo |
| `research_write_report` | Report Markdown final | `(research_id, custom_prompt=None) → str` | 5–30 s | LLM-free se custom_prompt=None |

### Resource (1)

- `research://{topic}` — context direto (sem session). Percent-decode server-side.

### Prompts (4) ✨ new in v3.0

| Prompt | Quando usar |
|---|---|
| `research_query(topic, goal?, report_format?)` | Workflow completo (deep + report) |
| `research_quick_brief(topic)` 🆕 | Raw snippets sem síntese (atalho, sem LLM) |
| `research_synthesis(research_id, audience?, length?)` 🆕 | Re-formata research existente por audience (general / executive / technical / academic) |
| `research_health_diagnose(symptoms)` 🆕 | Triagem de erros via `/health` + `/metrics` (decision tree retry/rephrase/escalate/report) |

---

## ⚙️ Configuration in percival.OS (Nanobot)

### Quickstart (v3.0.0 — recommended)

The server uses **a single inference endpoint** (one LLM). Same setup works
for **any** OpenAI-compatible gateway (OpenAI, Venice, MiniMax, OpenRouter,
local LLMs, etc.):

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
        "INFERENCE_BASE_URL": "https://api.minimax.io/v1",
        "INFERENCE_LLM": "minimax:MiniMax-M3",
        "RETRIEVER": "duckduckgo"
      },
      "tool_timeout": 300
    }
  }
}
```

> **⚠️ Use literals** — `INFERENCE_LLM=${INFERENCE_LLM:-default}` e similares são **template bash-style não-interpolados**. v3.0 detecta isso e emite WARN, mas a pipeline quebra silenciosamente se não trocar. Em caso de dúvida, copie valor direto: `INFERENCE_LLM=openai:gpt-4o-mini`.

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
+ "RETRIEVER": "duckduckgo"   // ou "brave" + BRAVE_API_KEY se quiser
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

---

## ⚠️ Known Limitations (v3.0.x)

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
cd percival.OS_Dev
uv sync
uv run percival-deep-research
```

### Test runs

```bash
# Whole suite (353 passed + 3 skipped; no integration deps needed).
uv run pytest -q

# Just the round 4+5 regression tests (placeholder detection, dedup, etc.).
uv run pytest tests/test_audit_round4_nano.py tests/test_audit_round5_placeholder.py -v

# Smoke test (boots, version prints):
INFERENCE_API_KEY=sk-fake INFERENCE_BASE_URL=https://api.minimax.io/v1 \
  INFERENCE_LLM=minimax:MiniMax-M3 \
  timeout 4 uv run --no-sync percival-deep-research
```

---

## 🛟 Troubleshooting (v3.0.x)

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
This server is an integral module of the **percival.OS** project. It enables Nanobot to perform complex research tasks that require multiple steps of validation and synthesis.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---

## 📝 Versioning

| Version | Status | Notes |
|---|---|---|
| 3.0.0 | ✅ current | 4 new prompts; strict-bool on `include_context`; INFERENCE_LLM placeholder detector |
| 2.3.x | 🟠 superseded | last with `include_context='yes'` accepted |
| 2.2.x | 🟠 superseded | single-endpoint inference introduced |
| 2.1.x | 🟢 legacy | four-slot `FAST_LLM`/`SMART_LLM`/… model |
| 1.0.x | 🟢 legacy | initial release |

See [CHANGELOG.md](CHANGELOG.md) for the complete history.

---
*Developed with ❤️ by the percival.OS Team*