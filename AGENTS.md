<!--
Project-scoped agent instructions for `<positronic>` inside
`/home/bill/Projects/percival-deep-research`. Extends (does not replace)
the global `AGENTS.md`, `SOUL.md` and `USER.md`.
-->

## Owner and operating model

Bill Kopp (`bill.kopp.dev@gmail.com`) is the sole owner, operator, decision-maker,
and signatory for this application and its IaC. The company is Positronic Bean
Labs (PBLabs), website `labs.positronicbean.com`. Bill is the only person
currently working on these projects.

- A direct instruction or decision from Bill authorizes the work within its
  stated scope. Do not request a second approval, repeat an already recorded
  decision, or invent another owner/reviewer or handoff.
- Keep process proportional: use one canonical source of truth and record
  evidence once per relevant source revision or image ID. Link to that evidence
  instead of duplicating it across plans and reports. Run only checks relevant
  to the changed risk; do not repeat equivalent checks as separate acceptance
  gates.
- An instruction authorizes only its stated scope. Do not infer production
  changes or publication from approval of local work or a test rollout.
- Before a runtime mutation, verify the target and its current image/configuration
  and preserve a practical rollback path. Use the owning manager and its
  supported interface; never edit manager state by hand. This is an operational
  safety check, not an additional approval gate.

## Working conventions

- Lint/format: `uv run --with ruff ruff check .` + `uv run --with ruff ruff format .`.
- Tests: `uv run pytest -q` (coverage `>=70%` enforced by the canonical
  command itself, via `addopts` in `pyproject.toml`).
- Patch `gpt-researcher`: run `uv run python scripts/patch_gpt_researcher.py`
  after each `uv sync` until upstream fixes `NameError: name 'Any'`. The script
  is a no-op for unaffected versions and refuses unsupported versions.
- Research runs in an isolated worker process
  (`percival_research/research_worker.py`); the parent enforces the timeout and
  kills the worker. Do not move the pipeline back in-process.
- Conventional Commits; scope = area afetada.
- Preserve hardening in every change: external content remains wrapped in an
  XML envelope or prefixed with `[SECURITY WARNING:...]`.

## Verification

- For code changes, run the canonical `uv run pytest -q` and the CI lint/format
  checks relevant to the change. Use the existing Docker probes when changing
  the corresponding image, transport, timeout, or build behavior.
- Provider-backed smoke tests are opt-in; never use real credentials unless
  Bill's request explicitly includes that test.
- For a candidate image scan, record Trivy version/database, source SHA, and
  image ID. The current `scripts/check_trivy_findings.py` checks that reported
  vulnerability IDs occur in the supplied VEX; it does not verify image-ID
  binding or an owner signature. Do not treat that script alone as satisfying
  those requirements. Create and sign the VEX once for the exact candidate
  image, as required by the applicable plan.
- Reuse test output for the exact revision/image across the plan and reports by
  reference; do not rerun or restate equivalent checks solely to satisfy
  duplicate paperwork.

## Deferred questions

- Automate `scripts/patch_gpt_researcher.py` in CI/pre-commit?
- Branching strategy for LTS (HEAD directly on `main` until v3.0.0)?

## Docker MCP operations

- Preserve the documented stdio/HTTP transport contract. Stdio stdout is
  JSON-RPC-only and must not use an HTTP healthcheck; check the configured mode
  before interpreting Docker health.
- Compose is a local fixture, not the source of truth for a managed runtime.
  Percival and Positronic retain separate state and supported interfaces.
- Keep provider-backed smoke tests opt-in and isolated from real accounts.
- Do not expose provider credentials in reports or logs.
