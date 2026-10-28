# Security note — candidate image `percival-deep-research:stage2-candidate`

**Date:** 2026-10-28 · **Tool:** Trivy 0.76.1 (vulnerability scan, image mode) ·
**Image:** `percival-deep-research:stage2-candidate` ·
**Image ID:** `sha256:afb0df3cc6b67e5bf01ac4bf018f0e6aba680b5a8c0271a8540c8c9e248aa150` ·
**Build inputs:** `python:3.12-slim@sha256:6b25cbe6…`, `gpt-researcher==0.16.0`,
`python 3.12.16`, Debian forky runtime stage.

## Findings

11 findings, all in the Python dependency chain pulled by `gpt-researcher==0.16.0`:

| Severity | Package | Installed | Fixed in |
|---|---|---|---|
| CRITICAL | authlib | 1.7.2 | 1.9.0 |
| HIGH | authlib | 1.7.2 | 1.9.0 / 1.9.1 |
| HIGH | dnspython | 2.8.0 | 2.9.0 |
| HIGH | litellm | 1.93.2 | 1.104.0-rc.2 |
| HIGH | litellm | 1.93.2 | 1.95.0 |
| MEDIUM | authlib | 1.7.2 | 1.9.0 |
| LOW | authlib | 1.7.2 | 1.8.0 |

Full list with per-statement justifications: `docs/security/vex-2026-10-28.json`.

## Owner decision (2026-10-28)

The owner chose to **keep the current dependency versions** in this
remediation round. The findings are therefore recorded as
`under_investigation` in the VEX document, not as `not_affected`: the
affected packages are present and reachable inside the image, and the
server does not expose the Authlib OAuth/OIDC server surface nor the
LiteLLM proxy/admin surface — that is a property of how this product is
deployed, not a fixed code path.

This is an open risk, not a closed finding. The upgrade path
(authlib >= 1.9.1, dnspython >= 2.9.0, litellm >= 1.104.0-rc.2) remains
tracked and must be resolved before publication in Etapa 2, or the VEX
status updated with a new dated decision.

## Reproducing the scan

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:0.76.1 image --scanners vuln --format json \
  percival-deep-research:stage2-candidate
```

The scan reads the local Trivy database; the DB date must be recorded
alongside the result, since a stale DB understates the exposure.
