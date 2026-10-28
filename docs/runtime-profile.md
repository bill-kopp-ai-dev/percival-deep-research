# Runtime profile required by the Deep Research MCP

**Status:** declared by the product; **application is owned by the managers**
(Percival / nanobot broker). This file states what the image expects from
whoever runs it. It does not change any running container.

## Why the product cannot enforce this itself

The image ships the security posture it can control (non-root `percival`
UID 1000, no init embedded, no `apt`, no setuid binaries). The remaining
posture — read-only rootfs, capability drop, `no-new-privileges`, the
secret mount, network profile — is decided by whoever creates the
container. The `docker-compose.yml` in this repository encodes the
reference profile; the managers must reproduce it.

## Reference profile

| Control | Value | Rationale |
|---|---|---|
| `user` | `1000:1000` | Matches the image's `percival` account (UID/GID 1000). |
| `read_only` | `true` | The server writes nothing outside the mounted paths; the rootfs stays immutable. |
| `cap_drop` | `ALL` | The server needs no Linux capabilities. |
| `security_opt` | `no-new-privileges:true` | Blocks setuid escalation. The image has no setuid binaries left. |
| `init` | `true` | **The launcher owns the init layer.** The image deliberately embeds no init, so a second supervisor would mask which process answers `SIGTERM`. |
| `capabilities` | none added | `CAP_DAC_OVERRIDE`/`CAP_NET_BIND_SERVICE` are unnecessary: the server listens on 8000 (>1024) as a non-root user. |
| `pids_limit` | e.g. `256` | The research pipeline runs one short-lived worker process per call; the limit bounds runaway fan-out. |
| `tmpfs` | `/tmp:size=64m,mode=1777,noexec,nosuid,nodev` | Scratch space for the worker, not persisted. |
| `network` | default bridge or an internal network | Outbound access is required **only** to the configured inference endpoint and retriever. See the network policy below. |

## Mounts

| Path | Mode | Content |
|---|---|---|
| `/app/.env` | read-only bind, host file mode `0600` | `INFERENCE_API_KEY`, `INFERENCE_BASE_URL`, `INFERENCE_LLM`, optional `BRAVE_API_KEY`. **Never** passed as environment variables and never copied into the container filesystem. |
| `/app/logs` | bind, UID 1000 writable | Server logs. |
| `/app/reports` | bind, UID 1000 writable | Report artifacts (the server returns reports as text; this path exists for operator-side exports). |

Do not mount a host package cache (`/var/cache/pacman/pkg`,
`/var/cache/apt`, a shared pip cache) into the container. The broker
runtime currently does this; the image no longer needs a package manager
(`apt` was removed from the runtime stage), so such a mount is a writable
host path exposed to the process with no consumer.

## Network policy

The image preloads the `o200k_base` tiktoken encoding and uses LiteLLM's
bundled model-cost map, so **startup and pipeline initialization do not
download metadata from the Internet**. The only outbound traffic the
server generates is to:

1. the configured inference endpoint (`INFERENCE_BASE_URL`), and
2. the configured retriever (`RETRIEVER=duckduckgo` by default; `searx`,
   `brave`, `tavily`, … also supported by the pinned upstream registry).

`/health` validates that the configured retriever exists in the embedded
`gpt-researcher` registry and that its required environment variables are
present. It does not check provider reachability or credential validity.

## What the managers must return

For each reconciliation (image/runtime), the owner of the manager returns:

- the image ID actually running and the `org.opencontainers.image.revision`
  label it carries;
- `docker inspect` evidence of `User`, `CapDrop`, `SecurityOpt`,
  `ReadonlyRootfs`, `Init` and `HostConfig.Mounts`;
- the network the container is attached to and the egress destinations
  actually needed by the inference endpoint and the retriever;
- the rollback path (previous image ID and previous configuration).

Application of this profile is a change to another system's runtime and
therefore requires the owner's approval; this repository only declares it.
