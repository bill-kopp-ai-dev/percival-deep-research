# Changelog — Percival Deep Research MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [Unreleased] — 2026-09-27

### 🐳 Docker encapsulation — compatível com Nanobot, OpenCode e Docker MCP Toolkit

Surface pública **preservada** (5 tools + 1 resource + 4 prompts — inalterado).
Mudança puramente operacional de packaging.

#### Added

- **Dockerfile multi-stage** (builder `ghcr.io/astral-sh/uv:python3.11-bookworm-slim`
  → runtime `python:3.11-slim`) com aplicação automática do patch
  `gpt-researcher >= 0.16.0` no stage de build (resolve
  `NameError: name 'Any'` no import).
- **`.dockerignore`** rigoroso — bloqueia `.venv`, `.git`, `.env`, caches
  (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.coverage*`) e artefatos
  de tooling. Sem ele o build context poluía a imagem com o venv do host.
- **Labels OCI + MCP** (`org.opencontainers.image.{title,source,licenses,version,…}`
  + `io.modelcontextprotocol.server.name=percival-deep-research`) para
  catalog e gateway do Docker MCP Toolkit.
- **Usuário não-root** `percival` (UID 1000) + **tini** como PID 1 para
  forwarding correto de `SIGTERM`.
- **Default transport = `stdio`** dentro da imagem — compatível com Nanobot,
  OpenCode, Claude Desktop e Docker MCP gateway (todos esperam stdio via
  `docker run -i`).
- **`docker-compose.yml`** modernizado: removida chave `version:` obsoleta,
  `RETRIEVER` default alinhado com `.env.example` (`duckduckgo`), `.env`
  marcado como opcional, profile `production` com nginx.
- **`docker/server.yaml` + `docker/tools.json` + `docker/README.md`** —
  metadata pronta para PR em `docker/mcp-registry` (publicação no
  hub.docker.com/mcp).
- **`scripts/docker_smoke_test.sh`** — boot real do container em ambos os
  transports, com `initialize` JSON-RPC sobre stdio e `curl /health` em
  SSE.
- **`tests/test_docker.py`** — 28 regressões estáticas: presença de
  `.dockerignore`, labels OCI/MCP, patch no build, non-root UID ≥ 1000,
  exec form do `ENTRYPOINT`, default `stdio`, ausência do auto-switch
  SSE em `server.py`, e validação do metadata do catalog.
- **Seção Docker no README** com snippets `mcp.json` prontos para Nanobot
  e OpenCode.

#### Changed (breaking para setups existentes)

- **Removido auto-switch para SSE em `server.py:110-112`.** Antes, quando
  `/.dockerenv` ou `DOCKER_CONTAINER=true` era detectado, o server forçava
  `transport = "sse"`. Isso **quebrou** todos os usos como MCP server
  stdio (Nanobot, OpenCode, Docker MCP gateway). Agora o transporte é
  puramente controlado por `MCP_TRANSPORT`; o default da imagem é `stdio`.
  Operadores que rodavam a imagem anterior em modo HTTP precisam setar
  `MCP_TRANSPORT=sse` explicitamente (ou usar `docker compose run` /
  `docker compose --profile production up`).

#### Fixed (na própria Dockerfile)

- O Dockerfile **anterior** não aplicava `scripts/patch_gpt_researcher.py`,
  então `gpt-researcher >= 0.16.0` quebrava em import dentro do container.
  A imagem antiga nunca bootou de fato em produção — agora boot via
  smoke test real em ambos os transports.

## [Unreleased] — 2026-09-27 (lint pass + image shrink)

### 🧹 Lint pass — 161 → 0 ruff errors + 46 → 0 files needing reformat

**Auto-fixável (149):**
- `F401` × 55 (imports não usados)
- `I001` × 49 (imports fora de ordem)
- `W292` × 40 (newline ausente no EOF)
- `F811` × 6 (redefinição de identificador)

**Manual (12):**
- 1 `F821` (dead code `_dr if False else _app` em `tests/test_audit_round3.py:88`
  — substituído por `_app` direto, era unreachable branch).
- 5 `F841` (vars locais não usadas em tests — renomeadas para `_var`).
- 5 `E402` (imports mid-file movidos para o topo em `utils.py:610-612`;
  2 mantidos no local de uso com `# noqa: E402` em `utils.py:825` e
  `tests/test_v22_simplification.py:223`).

**Bug real encontrado pelo lint:**
`tests/test_audit_round3.py:88` tinha o ramo morto
`_dr if False else _app` — `_dr` nunca foi importado; o branch sempre
resolvia para `_app`. Removido pelo ruff `F821`. Sem impacto em runtime
mas é indicador de código incompleto deixado num round de bug-hunt.

**Regressão evitada:** o auto-fix removeu 5 imports que pareciam não
usados mas eram re-exports para tests (`metrics`, `registry`,
`research_limiter`). Restaurados manualmente com `# noqa: F401` (testes
fazem `from server import metrics`, etc.).

**Resultado:**
- `uv run --with ruff ruff check .` → **All checks passed**
- `uv run --with ruff ruff format --check .` → **53 files already formatted**
- `uv run pytest -q` → **410 passed, 4 skipped** (zero regressão; +2
  testes novos para Dockerfile em `tests/test_docker.py`).

### 📦 Imagem Docker — 1.7 GB → 1.37 GB (–330 MB, –19.4%)

**Causas do inchaço identificadas via `du`:**

| Categoria | Tamanho | Causa |
|---|---|---|
| `__pycache__/` no venv | **121 MB** | Conflito entre `UV_COMPILE_BYTECODE=1` (força compilação) e `PYTHONDONTWRITEBYTECODE=1` (proíbe). uv honrou `UV_COMPILE_BYTECODE` e gravou `.pyc`. |
| `tests/` em packages | **49 MB** | Nenhum lido em runtime (só por pytest). |
| `.dist-info/` | **11 MB** | Usado por `importlib.metadata` — mantido. |
| `*.pyi` (type stubs) | **2.7 MB** | Só mypy/pyright usam. |

**Ações aplicadas (todas no builder stage, sem risco para runtime):**
1. **Removido `UV_COMPILE_BYTECODE=1`** do Dockerfile. `PYTHONDONTWRITEBYTECODE=1`
   sozinho garante zero `.pyc`. Custo: ~1-2% mais lento no primeiro
   import por execução do container (uma vez por lifetime).
2. **Etapa de cleanup** que remove:
   - `tests/` e `test/` em `site-packages/*` (~49 MB)
   - `*.pyi` (~2.7 MB)
   - `*.dist-info/RECORD` e `INSTALLER` (pip uninstall bookkeeping,
     não usado em runtime; mantém `METADATA` e `entry_points.txt`)

**Não aplicado (fora de escopo, alto risco):**
- Remover `spacy`/`llvmlite`/`numba` (~340 MB combinados) — transitivo
  do `gpt-researcher`; remover pode quebrar import interno.
- Trocar `python:3.11-slim` por `alpine` (~50-100 MB) — musl/glibc
  incompat em algumas deps (cryptography, grpcio).

**Verificações:**
- `docker build` → sucesso em ~30 s (cache quente)
- `bash scripts/docker_smoke_test.sh` → stdio ✅ + HTTP/SSE ✅
- `uv run pytest -q` → **410 passed, 4 skipped** (sem regressão)



## [3.0.1] — 2026-09-27

### 🐛 Bug-hunt round 6 — 14 issues fixed in deep_research, utils, health, observability

**Bumps:** v3.0.0 → v3.0.1 (semver-patch: bug fixes only; surface pública preservada).

**Headline metrics:**
- **14 bugs fixed** across `deep_research`, `utils`, `health`, `quick_search`, `write_report`,
  `resources`, `llm_bridge`, `prompts_versions`, `cache`, `patches`.
- **28 regression tests** added em `tests/test_audit_round6_bughunt.py`.
- Cobertura sobe de ~85% para **88.88%** (`uv run pytest --cov`).

### Fixed

#### Contrato público preservado (5 tools + 1 resource + 4 prompts — inalterado):

- **B1 (CRITICAL) — dedup waiter exception leak.** Quando o creator do `_IN_FLIGHT`
  é rejeitado pelo rate limiter, a Future compartilhada recebia uma exceção crua
  (`RuntimeError`) e qualquer waiter fazia `return await existing` → re-raise cru.
  Agora o waiter captura via `handle_exception`, devolvendo mensagem
  `Error: ... (correlation_id=...)` em vez de vazar stack trace.
- **B2 (HIGH) — `_do_deep_research` re-levantava exceção crua.** Substituído `raise`
  por `return handle_exception(...)` — alinhado com o padrão de `get_research_context`,
  `get_research_sources`, `write_report`.
- **B3 (HIGH) — `RateLimiter.release` podia liberar semáforo errado.** Se
  `_recreate_sem` rodava entre acquire e release (loop-mismatch), `release()`
  liberava o semáforo NOVO enquanto o original ficava permanentemente saturado.
  Adicionado contador `_pending` (atômico com `_lock`) que desacopla release
  da identidade do semáforo atual.
- **B4 (HIGH) — `Metrics.record_latency` ignorava operations sem campo dataclass.**
  `research_resource`, `get_research_context`, etc. não incrementavam counter
  (`hasattr` falhava silenciosamente). Substituído por `defaultdict(int)` interno
  `_totals`, exposto em `snapshot()['totals_by_tool']`.
- **B5 (MEDIUM) — `quick_search_total` / `write_report_total` nunca incrementavam.**
  Caminho de sucesso agora chama `record_latency` (no `finally`) — alinhando
  `/metrics` com a realidade do tráfego. Também trocado `metrics` importado por
  `_app.metrics` (runtime lookup) para honrar patches em testes.
- **B6 (MEDIUM) — `/health` reportava `"version": "2.2.0"` hardcoded.** Agora lê
  `percival_research.__version__` (3.0.0+), single source of truth.
- **B7 (MEDIUM) — `_check_retriever_configured` aceitava retriever desconhecido
  como configurado.** `RETRIEVER=bing` retornava `True` (healthy mentiroso). Agora
  valida contra `percival_research.retrievers._REGISTRY`.
- **B8 (MEDIUM) — `populate_inference_slots` substring match `"openai:"`**
  aceitava falsos positivos (`custom-openai-compatible:foo`). Trocado por
  `startswith("openai:")`.
- **B9 (MEDIUM) — `resources.py` timeout path não alimentava deque de latências.**
  Adicionado `record_latency("research_resource", elapsed_ms)` na branch
  TimeoutError — p50 deixa de ser enviesado em direção aos sucessos rápidos.
- **B10 (MEDIUM) — `_evict_expired` / `_evict_expired_cache` logavam 1 INFO por
  item expirado** (flood em registry saturado). Agora 1 mensagem agregada
  com a contagem total.
- **B11 (LOW) — `validate_research_id` não capturava `TypeError`** (`UUID(12345)`
  levanta `TypeError`, não `ValueError`). Adicionado ao `except`.
- **B12 (LOW) — `cache.ttl_s=0` tratado como "sem expiry"** (falsy). Agora
  `is None` é a checagem correta; `ttl_s=0` expira imediatamente.
- **B13 (LOW) — `format_context_with_sources` O(n²) em whitespace collapse.**
  Trocado `while "  " in s: replace()` por `re.sub(r" {2,}", " ", s)`.
- **B14 (LOW) — `prompts_versions` usava `print(..., file=sys.stderr)`** em vez
  de `logger.warning`. Alinhado com o resto do projeto.
- **B15 (LOW) — `_translate_all_slots` tinha `seen: set[str]` dead code.** Removido.
- **B16 (LOW) — `scripts/patch_gpt_researcher.py` inseria em posição errada**
  (depois de outros imports), quebrando com `SyntaxError` em 0.16.1+. Reescrito
  para detectar docstring e inserir como PRIMEIRA linha executável;
  também deduplica `from __future__` em re-aplicações.

## [3.0.0] — 2026-07-23

### 🎯 Major release — consolidation of 4 Nano bug-hunt rounds + 2 internal code-reviews

**Bumps:** v2.3.x → v3.0.0 (semver-major: surface expansion + schema strictness
on `include_context`).

**Headline metrics:**
- **48 bugs closed** across 4 official Nano bug-hunt rounds + 2 internal code-reviews.
- **151 regression tests** added on top of the v2.1 baseline.
- **+3 prompts** (surface 1 → 4); **+0 tools** (kept 5); **+1 fix on tool shape**
  (StrictBool on `include_context`).

### Added

#### Surface (5 tools + 1 resource + 4 prompts) — stable since v2.2.0 except for the 3 new prompts in v3.0:

| Surface element | Notes |
|---|---|
| `research_deep(query, include_context: StrictBool=False)` | Tool; Pydantic StrictBool v3.0+ (was lax `bool`). |
| `research_quick_search(query)` | Tool. |
| `research_get_context(research_id)` | Tool. |
| `research_get_sources(research_id)` | Tool. |
| `research_write_report(research_id, custom_prompt=None)` | Tool. |
| `research://{topic}` | Resource template; percent-decode server-side. |
| **`research_query(topic, goal?, report_format?)`** | Prompt; existing v2.x feature. |
| **`research_quick_brief(topic)`** 🆕 | Prompt; raw-snippets shortcut, sem LLM. |
| **`research_synthesis(research_id, audience?, length?)`** 🆕 | Prompt; reformata research existente (`general`/`executive`/`technical`/`academic` × `tl_dr`/`short`/`medium`/`long`). |
| **`research_health_diagnose(symptoms)`** 🆕 | Prompt; triage de erros via `/health`+`/metrics` com decision tree (retry/rephrase/escalate/report). |

#### Server-side hardening:

- **`Pydantic StrictBool` on `include_context`** — rejects `'yes'`, `'false'`,
  `1`, `0`, `{}` at the framework layer (N8 fix). 8 framework-level regression
  tests cover this matrix.
- **`utils_loader` shim** — fixes the legacy `from utils import …` path-injection
  problem when the package is imported from outside `percival-deep-research/`.
- **`utils.PLACEHOLDER_OPENERS`** — single source of truth for `INFERENCE_LLM`
  placeholder detection (no more duplicate `_LIKELY_PLACEHOLDERS` /
  `_PLACEHOLDER_SIGNALS` lists).
- **`_warn_on_malformed_inference_llm`** in `llm_bridge.py` (S4) — wrapper
  delegating to `config._sanitize_inference_llm_or_warn`. Single WARN per boot
  (was 2 before A1 fix in review-5).
- **`deep_research.in-flight dedup`** (N7) — N parallel calls with the same
  topic share a single `asyncio.Future`. Race-window double-checked inside
  the lock; S3 fix adds `future.exception()` consumer to silence
  `Future exception was never retrieved` log noise.

#### Test infrastructure:

- `tests/conftest.py`: autouse `_skip_integration_tests_without_server` fixture
  probes `localhost:8000` and skips `@pytest.mark.integration` tests when
  no server is running. Configurable via `PERCIVAL_TEST_HOST` /
  `PERCIVAL_TEST_PORT`.
- New regression files:
  - `tests/test_audit_round3_nano.py` (16 tests; v3.0 part).
  - `tests/test_audit_round4_nano.py` (11 tests; v3.0 part).
  - `tests/test_audit_round5_placeholder.py` (13 tests).
  - `tests/test_prompt_research_query.py` (32 tests across 4 prompts).
  - `tests/test_audit_fixes.py` (8 dedup/rate-limit tests).
- Total: **353 passed, 3 skipped, 1 warning** in 7.04 s.

### Changed (low-priority, cosmetic)

- Documented `INFERENCE_LLM` placeholder detector and its heuristic boundaries
  inline in `utils.py`, `config.py`, and `llm_bridge.py`.
- `CHANGELOG.md` and `README.md` rewritten for v3.0 surface.
- Adjusted prompt body templates to use `!r` defense-in-depth on
  `audience`/`length` values (review-2 C1; even though they're allowlist-
  validated, prevents future injection if allowlist is ever loosened).

### Fixed (all 48 bugs across rounds 1-4 + reviews 1-2)

#### Round 1 (Nano shipping-bugs — 11 closed in v2.2.x backports)

| # | Bug | Fix |
|---|---|---|
| B1 | `research://topic com espaço` ⇒ `invalid domain character` | Server-side percent-decode. |
| B2 | (covered; see CHANGELOG v2.2.0) | — |
| B3 | 401 on Venice/MiniMax | Bridge to `OPENAI_*` namespace. |
| B4 | `pytest` reports `1 failed` | Autouse skip fixture. |
| B5 | `EMBEDDING_LLM=gpt-4o-mini` | Sensible default only if OpenAI-compatible. |
| B6 | `__version__=2.1.0` | Drift detector regression test. |
| B7 | `description='…'` placeholder | Real docstrings. |
| B8 | `Component already exists` | No-extra-commit + regression test. |
| B9-B11 | (see CHANGELOG v2.2.0) | — |

#### Round 2 (22 closed in v2.2.x)

Largamente backports de 2026-07-23 audit report. Não repetimos aqui; ver git
history (`git log --grep "audit-roda-2"`).

#### Round 3 (9 closed in v2.2.1, v2.3.x)

| # | Bug | Fix |
|---|---|---|
| B4 | `pytest -q` 1 failed | autouse fixture (real fix). |
| B6 | `__version__` drift | regression test. |
| B8 | `Component already exists` (template) | regression test. |
| B9 | (troubleshooting section in README) | — |

#### Round 4 (N1, N4, N6', N7, N8 — 5 closed in v2.3.x → v3.0)

| # | Bug | Fix |
|---|---|---|
| N1 | `quick_search` sem rate-limiter | Mirror `deep_research` acquire/release. |
| N4 | `get_research_sources` sem wrap | `wrap_untrusted_content`. |
| N6' | `goal=''` rejeitado | Default fallback ao goal vazio. |
| N7 | `deep_research` sem dedup in-flight | `_IN_FLIGHT` dict + `_IN_FLIGHT_LOCK`; Shared `asyncio.Future`. |
| N8 | `include_context` aceita string | `isinstance(..., bool)` guard no handler (S4-review fix). |
| N9 | Framework-level lax-coercion bypass | `Pydantic StrictBool` annotation (v3.0). |

#### Round 5 (`S4/S6/S3/S9` placeholder literal — closed in v2.3.3 → v3.0)

| Suggestion | Fix |
|---|---|
| S4 (MÉDIA) | Warn em `INFERENCE_LLM` malformado (`llm_bridge.py`). |
| S6 (BAIXA) | Validate `Settings.__init__` (single-sourced em `utils.PLACEHOLDER_OPENERS`). |
| S3 (BAIXA) | `future.exception()` em deep_research rate-limit-reject. |
| S9 (BAIXA) | Lock-in regression test for `report_format` echoing. |

#### Review round 1 (14 issues → 8 fixed, 5 cosmetic, 1 N/A)

Highlights: utils_loader shim (`from utils import ...` outside repo), Step 3 → Step 2 renumbering, whitespace → fallback for symptoms.

#### Review round 2 (C1+A1+M1 fix + 3 cosmetic)

| # | Issue | Fix |
|---|---|---|
| C1 (HIGH) | `}` false-positive on placeholder heuristic | Removed `}` from `PLACEHOLDER_OPENERS`. |
| A1 (HIGH) | WARN emitted twice (config + llm_bridge) | Single location: `config._sanitize_inference_llm_or_warn`. |
| M1 (LOW) | Decision tree "Step 3" without a "Step 2" | Added explicit "Step 2 — Apply the decision tree above" connector. |

### Deprecated

Following the v2.2.0 deprecation track — these still work in v3.0 with deprecation log but will be removed in v4.0:

- `OPENAI_API_KEY` — use `INFERENCE_API_KEY`
- `OPENAI_BASE_URL` — use `INFERENCE_BASE_URL`
- `PERCIVAL_LLM_PROVIDER_ALIASES` — auto-detected from URL
- `BRAVE_API_KEY` — only needed for `RETRIEVER=brave`

### Migration guide (v2.3.x → v3.0)

```diff
- await client.call_tool("research_deep", {"query": "x", "include_context": "yes"})
+ await client.call_tool("research_deep", {"query": "x", "include_context": True})
```

If you have agents that passed strings to `include_context`, they need a code
update. Sample workflow with the new prompts:

```python
# Before (v2.3): one prompt for everything
prompt = await client.get_prompt("research_query", {...})

# After (v3.0): dedicated prompt for each workflow
prompt = await client.get_prompt("research_query", {...})  # full
prompt = await client.get_prompt("research_quick_brief", {...})  # raw
prompt = await client.get_prompt("research_synthesis", {...})  # reformat
prompt = await client.get_prompt("research_health_diagnose", {...})  # triage
```

### Known limitations (v3.0.x)

See README "Known Limitations" section:
1. Embeddings require OpenAI-compatible provider (non-OpenAI providers fall back to in-process heuristics).
2. The four-slot override (`FAST_LLM`/`SMART_LLM`/…) without `INFERENCE_LLM` is brittle.
3. `gpt-researcher ≥ 0.16.0` upstream bug requires local patch (`scripts/patch_gpt_researcher.py`).
4. DuckDuckGo 429 under sustained scraping.
5. `include_context` schema strictness (v3.0 breaking — see migration).

---

## [2.3.x] — 2026-07-23

Combined changelog for v2.3.0 → v2.3.4. See git log: `git log --grep "v2.3"` for individual commits.

Highlights:
- v2.3.0 — Added 3 new prompts (`research_quick_brief`, `research_synthesis`, `research_health_diagnose`).
- v2.3.1 — Code-review fixes (utils_loader shim).
- v2.3.2 — Code-review-2 fixes (`!r` defense-in-depth, symptoms truncation, Step 1/2/3 renumbering).
- v2.3.3 — Addressed `INFERENCE_LLM` placeholder literal bug (S4/S6/S3/S9 fix).
- v2.3.4 — Tightened placeholder detection (removed `}` false-positive, single WARN emit location).

## [2.2.0] — 2026-07-23

### 🎯 Major simplification: single LLM endpoint

Aligns the MCP server with the Nanobot agent's own configuration:
one inference endpoint, one model, zero per-slot gymnastics.

### Added
- **`INFERENCE_API_KEY`** — single credential variable. Replaces `OPENAI_API_KEY`.
- **`INFERENCE_BASE_URL`** — single URL variable. Replaces `OPENAI_BASE_URL`.
- **`INFERENCE_LLM`** — single model variable. Replaces the four-slot
  `FAST_LLM` / `SMART_LLM` / `STRATEGIC_LLM` / `EMBEDDING_LLM` configuration.
- **`Settings.inference_provider_alias`** — auto-detected from `INFERENCE_BASE_URL`:
  - `https://api.venice.ai/api/v1` → `venice:`
  - `https://api.minimax.io/v1` → `minimax:`
  - `https://openrouter.ai/api/v1` → `openrouter:`
  - other OpenAI-compatible → `openai:` (no alias)
- **`RETRIEVER=duckduckgo` as new default** — no API key required. Matches
  the Nanobot CLI's default retriever.
- **`populate_inference_slots()`** — `llm_bridge.py` fills the four
  `STRATEGIC_LLM`/`FAST_LLM`/`SMART_LLM`/`EMBEDDING_LLM` from
  `INFERENCE_LLM` if the operator hasn't explicitly set them.
- New `_detect_provider_alias()` helper in `config.py`.
- New `_env_str_fallback()` helper that emits a deprecation warning when
  a legacy variable (`OPENAI_API_KEY`, etc.) is used.
- **`/health` schema updated** — `openai_configured` → `inference_configured`.
  Old key still works for backward compat at the server boundary.

### Changed
- **`run_server()`** logs `Inference provider`, `Inference LLM`, and
  `Default retriever` at startup for operational visibility.
- **`RETRIEVER` default** changed from `brave` to `duckduckgo`.
- **Error messages** in `run_server()` reference `INFERENCE_API_KEY` /
  `INFERENCE_BASE_URL` (with legacy fallback notice).

### Deprecated (will be removed in v3.0.0)
- `OPENAI_API_KEY` — use `INFERENCE_API_KEY`
- `OPENAI_BASE_URL` — use `INFERENCE_BASE_URL`
- `FAST_LLM`, `SMART_LLM`, `STRATEGIC_LLM`, `EMBEDDING_LLM` — these
  still work as **per-slot overrides** if you set them. If unset, all
  four slots are populated from `INFERENCE_LLM`.
- `PERCIVAL_LLM_PROVIDER_ALIASES` — auto-detected from URL. Setting
  this is now redundant for known providers.
- `BRAVE_API_KEY` (only required if `RETRIEVER` contains `brave`)

### Migration guide (v2.1.x → v2.2.0)
```diff
- OPENAI_API_KEY=sk-...
- OPENAI_BASE_URL=https://api.venice.ai/api/v1
- FAST_LLM=venice:llama-3.3-70b
- SMART_LLM=venice:llama-3.3-70b
- STRATEGIC_LLM=openai:gpt-4o-mini
- EMBEDDING_LLM=openai:text-embedding-3-small
- PERCIVAL_LLM_PROVIDER_ALIASES=venice:,minimax:,openrouter:
- RETRIEVER=brave
- BRAVE_API_KEY=...
+ INFERENCE_API_KEY=suas-chave
+ INFERENCE_BASE_URL=https://api.venice.ai/api/v1
+ INFERENCE_LLM=venice:llama-3.3-70b
+ # RETRIEVER default = duckduckgo; no API key needed
```

### Testes
- 9+ regression tests for the new config layer, LLM bridge, and health check.
- All 251+ existing tests still pass.

## [2.1.0] — 2026-07-22

Refactor completo executado em 8 fases incrementais (ver
`MCP_Docs/refactor_plans/percival-deep-research/`), seguido de 3 rodadas
de auditoria interna. Sem breaking change na API MCP pública (nomes de
tools, resource e prompt preservados).

### Added
- `config.py`: `Settings` (frozen dataclass) e `load_settings()` —
  toda constante de runtime (TTLs, caps, timeouts, rate limit) agora
  configurável via env `PERCIVAL_*`.
- `llm_bridge.py`: tradução isolada de `venice:`/`minimax:`/`openrouter:`
  → `openai:` para `FAST_LLM`/`SMART_LLM`/`STRATEGIC_LLM`/`EMBEDDING_LLM`.
- Pacote `percival_research/`: `server.py` modularizado em `app.py`,
  `tools/`, `resources.py`, `prompts.py`, `patches.py`, `health.py`,
  `metrics.py`, `retrievers/`, `cache/`, `prompts_versions.py`.
- `GET /health`: valida `OPENAI_API_KEY`/`OPENAI_BASE_URL` e o retriever
  configurado (retorna 503 quando degradado).
- `GET /metrics`: contadores por tool e latência p50.
- Timeout interno configurável em `deep_research` e no resource
  `research://{topic}` (`PERCIVAL_RESEARCH_TIMEOUT_S`, default 90s).
- Rate limiter (semáforo de concorrência) em `deep_research`
  (`PERCIVAL_MAX_CONCURRENT_RESEARCH`, default 3).
- TTL no cache de tópicos e nos researchers ativos, com evicção
  automática e `ResearchRegistry` thread-safe.
- `correlation_id` (`crl-xxxxxxxx`) em todas as respostas de erro.
- Validação de `research_id` como UUID RFC 4122 (qualquer versão, não só v4).
- Monkey-patch do `ContextCompressor` com guarda (checa existência da
  classe e assinatura do método antes de aplicar).
- Plugin pattern para retrievers (`percival_research/retrievers/`,
  DuckDuckGo + Brave) e para cache (`percival_research/cache/`,
  `InMemoryCache`).
- Versionamento de prompt via `PERCIVAL_PROMPT_VERSION` (v1/v2).
- Persistência opcional do cache de tópicos (`PERCIVAL_PERSIST_REGISTRY`).
- Cobertura de testes ≥ 70% (unit tests para as 5 tools, resource e prompt).

### Fixed
- Binário do Docker (`gptr-mcp` → `percival-deep-research`) no
  `Dockerfile`/`docker-compose.yml`.
- Versão divergente entre `pyproject.toml` e `README.md`.
- `deep_research` armazenava cache do resource sem o warning header de
  conteúdo não confiável em alguns caminhos — unificado.
- `GET /health` reportava "healthy" mesmo com `RETRIEVER=brave`
  configurado e `BRAVE_API_KEY` ausente (checagem considerava qualquer
  `RETRIEVER` setado como suficiente, sem validar a credencial exigida
  pelo retriever escolhido) — `deep_research`/`quick_search` falhariam
  em toda chamada real apesar do health check verde. Corrigido para
  validar a credencial específica do retriever ativo.
- `pyproject.toml` não declarava `pytest-cov` como dependência de dev
  nem `[tool.coverage.*]` — `uv sync --all-extras --dev` seguido de
  `pytest --cov-fail-under=70` (comando de verificação final do plano)
  falhava com `unrecognized arguments` em um ambiente limpo.
- Variável morta em `write_report`, imports redundantes de `uuid` em
  `server.py`, registro duplicado de `GPTResearcher` vazio no
  `research_id` (bug que teria quebrado `write_report`/
  `get_research_sources`/`get_research_context` para toda pesquisa nova).

## [1.0.0] — 2026-07-22

### Security
- Input sanitization for all parameters (prompt injection, length limits).
- Web content prefixed with untrusted-content warning header.
- Generic error messages to prevent internal information leakage.
- UUID v4 validation for `research_id`.
- Secure default host binding (127.0.0.1) for SSE mode.