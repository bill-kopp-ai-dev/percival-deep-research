<!--
Project-scoped agent instructions for `<positronic>` inside
`/home/bill/Projects/percival-deep-research`. Extends (does not replace)
the global `AGENTS.md`, `SOUL.md` and `USER.md`.
-->

## Working conventions

- Lint/format: `uv run --with ruff ruff check .` + `uv run --with ruff ruff format .`.
- Tests: `uv run pytest -q` (cobertura `>=70%` enforced).
- Patch gpt-researcher: `uv run python scripts/patch_gpt_researcher.py`
  apos cada `uv sync` (mandatory ate upstream resolver
  `NameError: name 'Any'`).
- Conventional Commits; scope = area afetada.
- Hardening preservado em toda mutacao: conteudo externo continua wrappado
  por XML envelope ou prefixo `[SECURITY WARNING:...]`.

## Verification

- `uv run pytest -q` (canonical, com cobertura embutida).
- `uv run --with ruff ruff check .` + `ruff format --check .` (pre-commit).
- Smoke ao vivo (opt-in) contra credenciais reais, exercitando
  `research_deep` ponta-a-ponta.

## Open questions

- Automatizar `scripts/patch_gpt_researcher.py` em CI / pre-commit?
- Estrategia de branchamento para LTS (HEAD em `main` direto ate v3.0.0)?


## Docker MCP operations

- Keep the image's documented stdio/HTTP transport contract; stdio stdout is
  JSON-RPC-only and must not use an HTTP healthcheck. Verify the exact mode
  before interpreting Docker health.
- The owning manager controls production containers; Compose is a local fixture.
  Percival and Positronic have separate state and supported interfaces.
- Before mutation, identify owner, image ID, revision, mounts/data and rollback;
  use only the owning manager with freshly read CAS values. Never edit state by
  hand or expose provider credentials in reports.
- Keep provider-backed research smoke opt-in and isolated from real accounts.
  Verify MCP handshake and a safe fixture response before/after rollback.
