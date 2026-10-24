# Percival Deep Research

## Purpose and intended outcome

Manter e evoluir o servidor MCP `percival-deep-research` em producao, dando ao
Nanobot capacidades autonomas, persistentes e seguras de pesquisa web
multi-source com validacao cruzada. Parte do ecossistema percival.OS
(Personal Agentic Operating System).

Sucesso = Nanobot rodando o fluxo completo de pesquisa + relatorio sem
regressao no contrato publico, hardening preservado, e suite de testes
verde.

## Scope and success criteria

1. **Contrato publico preservado** -- 5 tools (`research_deep`,
   `research_quick_search`, `research_get_context`, `research_get_sources`,
   `research_write_report`) + 1 resource (`research://{topic}`) + 4 prompts
   (`research_query`, `research_quick_brief`, `research_synthesis`,
   `research_health_diagnose`). Mudanca de nome/schema/semantica e breaking
   change -- coordenar com o time do consumidor Nanobot antes de versionar.
2. **Suite verde** -- `uv run pytest -q` verde, cobertura embutida
   `>=70%` (enforced em `[tool.coverage.report].fail_under`).
3. **Hardening preservado** -- defesa contra prompt injection + isolamento
   de conteudo web nao-confiavel (XML envelopes em read paths, prefixo
   `[SECURITY WARNING:...]` em `research_get_*`).
4. **Lint/format limpos** -- `uv run --with ruff ruff check .` e
   `uv run --with ruff ruff format .`.
5. **Disciplina de bug-hunt** -- cada fix vem com regressao em `tests/`
   (precedente: rounds 2-5 + code-review 2, 48 bugs fechados ate v3.0.0).

Evidencia de "funcionou": smoke contra o binario real (`research_deep`
ponta-a-ponta com gateway OpenAI-compatible + `research_get_sources` +
`research_write_report`) **e** regressoes em `tests/` para cada bug
corrigido.

## Methods and resources

- Python `>=3.11`, build via `hatchling` (`pyproject.toml`).
- Runtime: `gpt-researcher>=0.14.0`, `fastmcp>=3.2.0,<4.0.0`,
  `loguru>=0.7.0,<1.0.0`, `langchain`, `langchain-mcp-adapters`,
  `langchain-community`, `python-dotenv>=1.1.1`. Venv + deps via `uv`.
- Testes: `pytest>=9`, `pytest-asyncio>=1.3.0`, `pytest-cov>=5`,
  `httpx>=0.27`, `sseclient-py>=1.7`. Marker `integration` para testes
  que exigem servidor SSE rodando em outro terminal.
- Lint/format: `ruff` (`line-length=100`, `target-version=py311`, regras
  `E,F,I,W`, ignora `E501`).
- Layout: `server.py`, `config.py`, `llm_bridge.py`, `utils.py` no root;
  `percival_research/` (subpacote: `app.py`, `health.py`, `metrics.py`,
  `prompts.py`, `resources.py`, `retrievers/`, `tools/`, `cache/`,
  `patches.py`); tests em `tests/`.
- **Patch obrigatorio pos-`uv sync`:** rodar
  `uv run python scripts/patch_gpt_researcher.py` para corrigir
  `NameError: name 'Any'` no `gpt-researcher >= 0.16.0` upstream.
- **Single-endpoint inference:** `INFERENCE_API_KEY` + `INFERENCE_BASE_URL`
  + `INFERENCE_LLM=<provider>:<model>` (OpenAI-compatible). Retriever:
  `duckduckgo` (default) ou `brave` (requer `BRAVE_API_KEY`).
- Console script: `percival-deep-research = "server:run_server"`.
- Sem GPU; sem treino de modelo; CI `.github/`.

## Risks and governance

1. **Upstream `gpt-researcher >= 0.16.0`.** Bug `NameError: name 'Any'` na
   importacao. Mitigado por `scripts/patch_gpt_researcher.py`; precisa ser
   re-aplicado apos qualquer `uv sync`.
2. **Drift upstream.** `fastmcp`, `gpt-researcher`, `langchain` podem
   mudar comportamento. Lockfile + CI + rounds de bug-hunt pass com
   regressao em `tests/`.
3. **Drift de configuracao.** Placeholders bash-style
   (`${INFERENCE_LLM:-default}`) em `.env`/`config.json` quebram
   silenciosamente a pipeline. Loader emite WARN `[S6]` na v3.0; operador
   deve usar literais.
4. **Embedding slot em gateway custom.** Quando
   `INFERENCE_LLM=minimax:...` (ou `venice:`, `openrouter:`, etc.), o slot
   de embedding fica unset por design (v3.0). `populate_inference_slots()`
   propaga `OPENAI_*` para `gpt-researcher/memory/embeddings.py`
   automaticamente.
5. **Rate-limit do retriever.** DuckDuckGo retorna `HTTP 429` em trafego
   sustentado. Operadores encadeando research em lote devem considerar
   Brave (`BRAVE_API_KEY`) ou SearXNG local.
6. **Strict-bool `include_context` (v3.0+).** `Pydantic StrictBool`
   rejeita `'yes'`, `'false'`, `1`, `0`, `dict`, etc. antes do handler
   rodar -- breaking vs v2.x.
7. **Public contract changes** (tool name / schema / semantica) sao
   breaking -- coordenar com o time do consumidor Nanobot antes de
   versionar.
8. **Local-first / privacidade.** Todo processamento acontece localmente;
   nenhuma chamada envia contexto para o ecossistema percival.OS sem
   consentimento explicito. API keys do operador nao sao logadas.
9. **Licenca MIT** mantida; copyright `percival.OS contributors`.

## Working conventions

- Lint/format: `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format .` (regras `E,F,I,W`, `line-length=100`,
  `target-version=py311`).
- Tests: `uv run pytest -q` (cobertura embutida `>=70%` enforced em
  `[tool.coverage.report].fail_under`). Integracao opt-in:
  `uv run pytest -m integration` (requer `MCP_TRANSPORT=sse uv run
  --no-sync percival-deep-research` em outro terminal).
- Patch gpt-researcher: `uv run python scripts/patch_gpt_researcher.py`
  apos `uv sync` (mandatory ate upstream resolver).
- Markdown table cells intencionalmente ignoram `E501` (lidos por humanos,
  nao pelo lint layer).
- Manutencao corretiva: cada fix vem com regressao em `tests/` que falha
  sem o patch (precedente: rounds 2-5 + code-review 2).
- Conventional Commits; scope = area afetada (ex.:
  `fix(llm-bridge): ...`, `feat(prompts): ...`).
- Hardening preservado em qualquer mutacao: conteudo externo (web snippets,
  fontes) continua wrappado por XML envelope ou prefixo
  `[SECURITY WARNING:...]`.

## Verification

- Canonical: `uv run pytest -q` (cobertura embutida, `fail_under=70`,
  `show_missing=true`).
- Opcional: `uv run --with ruff ruff check .` e `ruff format --check .`.
- Live smoke (opt-in, fora do CI padrao): boot do servidor contra
  credenciais reais e exercitar `research_deep` + `research_get_sources` +
  `research_write_report` ponta-a-ponta. Bloco
  `timeout 4 uv run --no-sync percival-deep-research` no README mostra o
  smoke rapido (boot + version).

## Open questions

- **Patch do gpt-researcher em CI.** Hoje
  `scripts/patch_gpt_researcher.py` so roda manual apos `uv sync`.
  Promover para pre-commit ou hook de CI para evitar drift quando o venv
  e recriado?
- **Estrategia de branchamento.** HEAD esta em `main` direto
  (v3.0.1). Sem `release/x.y.z` branches visiveis. Vale
  formalizar quando v3.x for declarada LTS?
