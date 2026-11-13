<!--
Project-scoped agent instructions for `<positronic>` inside
`/home/bill/Projects/percival-deep-research`. Extends (does not replace)
the global `AGENTS.md`, `SOUL.md` and `USER.md`.
-->

## Owner and operating model

Bill Kopp is the sole owner, developer, operator, approver, decision-maker, and
signatory for this application and its infrastructure as code (IaC).

- Contact: `bill.kopp.dev@gmail.com`.
- Company: Positronic Bean Labs (PBLabs).
- Website: <https://labs.positronicbean.com>.

- A direct instruction or decision from Bill authorizes the work within its
  stated scope. Do not request a second approval, repeat an already recorded
  decision, or invent another owner, team, reviewer, signer, or handoff. Changes
  affecting Nanobot or shared IaC are coordinated with Bill in those scopes.
- Tests, checks, scans, and reviews provide evidence; they are not approvals.
  Completion requires the requested outcome and relevant verification, not a
  separate acceptance ceremony, dual-agent validation, or third-party sign-off.
- Apply Bill's current decisions when older project briefs, plans, or reports
  describe additional reviewers, duplicate acceptances, or superseded gates.
  Historical records are evidence, not new authorization requirements. Surface
  material conflicts with current technical requirements rather than silently
  bypassing them.
- An instruction authorizes only its stated scope. Do not infer production
  changes or publication from approval of local work or a test rollout.
- When Bill requests commit and push to `main`, perform them after the relevant
  checks; do not add a pull request, release branch, or another confirmation.

## Minimum necessary process

- Use the smallest set of checks that addresses the change and its actual
  failure modes. Do not add cross-validation, repeated proofs, committees,
  approval stages, or configuration switches without a concrete need.
- Keep one canonical record for each material decision or result. Link to
  existing evidence instead of copying it into multiple plans and reports.
  Routine work needs a concise change/verification summary, not a new dossier.
- Reuse valid evidence for the same relevant source revision, configuration, or
  image ID. Repeat a check only when a relevant input changed, evidence is stale,
  a failure needs investigation, or the earlier result is inconclusive. A
  documentation-only commit does not invalidate unchanged runtime evidence.
- Prefer existing defaults, commands, and supported interfaces. Add a setting
  only when a real operating requirement cannot be met by the current setup.
- Preserve enforced CI and runtime controls. Changing those controls is an
  explicit, scoped configuration change; do not invent manual equivalents or
  extra approval gates around them.
- Before a runtime mutation, verify the target and its current image/configuration
  and preserve a practical rollback path. Use the owning manager and its
  supported interface; never edit manager state by hand. This is an operational
  safety check, not an additional approval gate.

## Working conventions

- Lint/format checks: `uv run --with ruff ruff check .` and
  `uv run --with ruff ruff format --check .`. Use `ruff format` to apply formatting
  only when needed for the code being changed.
- Tests: `uv run pytest -q` (coverage `>=70%` enforced by the canonical
  command itself, via `addopts` in `pyproject.toml`).
- Patch `gpt-researcher`: run `uv run python scripts/patch_gpt_researcher.py`
  after each `uv sync` until upstream fixes `NameError: name 'Any'`. The script
  is a no-op for unaffected versions and refuses unsupported versions.
- Research runs in an isolated worker process
  (`percival_research/research_worker.py`); the parent enforces the timeout and
  kills the worker. Do not move the pipeline back in-process.
- Conventional Commits; scope = affected area.
- Preserve hardening in every change: external content remains wrapped in an
  XML envelope or prefixed with `[SECURITY WARNING:...]`.

## Verification

- For documentation-only changes (including this file), review accuracy, scope,
  and `git diff --check`. Do not run the Python suite, rebuild images, scan, or
  request live smoke tests solely for prose changes.
- For code changes, run the canonical `uv run pytest -q` and the CI lint/format
  checks relevant to the change. Add a regression test when it meaningfully
  demonstrates a corrected failure; do not create tests that merely restate the
  implementation or validate low-impact prose/configuration mechanically.
- For image, transport, timeout, or build changes, use the existing Docker probes
  that exercise the affected behavior. Do not require every probe for every
  change or repeat a valid result for a second acceptance.
- Provider-backed smoke tests are opt-in; never use real credentials unless
  Bill's request explicitly includes that test. An opt-in test is not a general
  completion or publication gate.
- For a candidate image scan, record Trivy version/database, source SHA, and
  image ID. `scripts/check_trivy_findings.py` checks that reported vulnerability
  IDs occur in the supplied VEX; it does not verify image-ID binding or an owner
  signature. Require those only when an applicable current control or explicit
  decision requires them; do not infer a universal signing ceremony from a
  historical rollout plan. Reuse Bill's recorded vulnerability decision while
  its scope and risk assumptions remain valid; reassess new findings or changed
  exposure and never claim coverage for an unverified image.
- Report what changed, which relevant checks ran and their results, and any
  concrete unresolved issue. Checks not needed for the scope are not blockers.

## Docker MCP operations

- Preserve the documented stdio/HTTP transport contract. Stdio stdout is
  JSON-RPC-only and must not use an HTTP healthcheck; check the configured mode
  before interpreting Docker health.
- Compose is a local fixture, not the source of truth for a managed runtime.
  Percival and Positronic retain separate state and supported interfaces.
- Do not expose provider credentials in reports or logs.
