# Changelog — Percival Deep Research MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- (placeholder para próximas mudanças)

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