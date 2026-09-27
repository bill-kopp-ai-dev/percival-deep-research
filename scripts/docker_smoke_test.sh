#!/usr/bin/env bash
# scripts/docker_smoke_test.sh — end-to-end smoke test for the MCP image.
#
# Verifies the image actually boots in BOTH stdio and HTTP/SSE modes:
#   1. Stdio: pipe a JSON-RPC `initialize` request over stdin and assert
#      the response contains `"jsonrpc"`.
#   2. HTTP/SSE: launch with `MCP_TRANSPORT=sse` and curl `/health`;
#      expect 200 + `{"status":"healthy",...}` (or `"degraded"` if the
#      dummy API key is rejected — that's still a successful boot).
#
# Requires: docker (BuildKit enabled — the default since Docker 23).
# Exits 0 on success, non-zero with a colored FAIL line on any failure.

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

IMAGE_TAG="${IMAGE_TAG:-percival-deep-research:smoke}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

# Dummy credential — the health check reports "degraded" but the server
# still boots (gpt-researcher is lazy-loaded, so credential errors don't
# fire until the first tool call).
DUMMY_KEY="${DUMMY_KEY:-smoke-test-dummy-key-not-real}"

# Colors only when attached to a terminal.
if [[ -t 1 ]]; then
    BLUE='\033[1;34m'
    GREEN='\033[1;32m'
    RED='\033[1;31m'
    RESET='\033[0m'
else
    BLUE=''; GREEN=''; RED=''; RESET=''
fi

log()   { printf "${BLUE}[smoke]${RESET} %s\n" "$*"; }
ok()    { printf "${GREEN}[smoke OK]${RESET} %s\n" "$*"; }
fail()  { printf "${RED}[smoke FAIL]${RESET} %s\n" "$*" >&2; exit 1; }

# ─── 1. Build ────────────────────────────────────────────────────────
log "Building image ${IMAGE_TAG} from ${DOCKERFILE}..."
BUILD_LOG="/tmp/percival-docker-build.log"
if ! docker build \
        --file "${DOCKERFILE}" \
        --tag "${IMAGE_TAG}" \
        --label "smoke.test=percival-deep-research" \
        "${PROJECT_ROOT}" >"${BUILD_LOG}" 2>&1; then
    tail -80 "${BUILD_LOG}"
    fail "docker build failed (see ${BUILD_LOG})"
fi
IMAGE_SIZE=$(docker images --format '{{.Size}}' "${IMAGE_TAG}")
ok "Image built (${IMAGE_SIZE})."

# ─── 2. Stdio smoke ──────────────────────────────────────────────────
log "STDIO smoke: JSON-RPC initialize over stdin..."
INIT_REQ='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke-test","version":"0.0.0"}}}'

STDIO_LOG="/tmp/percival-docker-stdio.log"
# `-i` keeps stdin open for the pipe; `--rm` cleans up; no `-t` (no TTY).
INIT_RES=$(printf '%s\n' "${INIT_REQ}" \
    | docker run --rm -i \
        -e INFERENCE_API_KEY="${DUMMY_KEY}" \
        -e INFERENCE_BASE_URL="https://api.openai.com/v1" \
        -e INFERENCE_LLM="openai:gpt-4o-mini" \
        -e RETRIEVER="duckduckgo" \
        -e MCP_TRANSPORT=stdio \
        -e LOG_LEVEL=WARNING \
        "${IMAGE_TAG}" 2>"${STDIO_LOG}") \
    || { tail -40 "${STDIO_LOG}"; fail "container exited non-zero in stdio mode"; }

# FastMCP frames responses with Content-Length headers + JSON body. We
# just check for a valid JSON-RPC marker in either form.
if ! grep -Eq '"jsonrpc"\s*:' <<<"${INIT_RES}"; then
    printf 'Response (first 800 chars):\n%.800s\n' "${INIT_RES}"
    printf '\nContainer stderr:\n'; tail -40 "${STDIO_LOG}"
    fail "STDIO: response did not look like JSON-RPC"
fi
ok "STDIO: got a JSON-RPC response from initialize."

# ─── 3. HTTP/SSE smoke ──────────────────────────────────────────────
log "HTTP/SSE smoke: launching container with MCP_TRANSPORT=sse..."
HTTP_CID=$(docker run --rm -d \
    -p 8000:8000 \
    -e INFERENCE_API_KEY="${DUMMY_KEY}" \
    -e INFERENCE_BASE_URL="https://api.openai.com/v1" \
    -e INFERENCE_LLM="openai:gpt-4o-mini" \
    -e RETRIEVER="duckduckgo" \
    -e MCP_TRANSPORT=sse \
    -e MCP_HOST=0.0.0.0 \
    -e PORT=8000 \
    -e LOG_LEVEL=WARNING \
    "${IMAGE_TAG}")
cleanup() { docker rm -f "${HTTP_CID}" >/dev/null 2>&1 || true; }
trap cleanup EXIT

HEALTH=""
HTTP_LOG="/tmp/percival-docker-http.log"
for _ in {1..40}; do
    if HEALTH=$(curl -fsS "http://127.0.0.1:8000/health" 2>/dev/null); then
        break
    fi
    sleep 1
done

if [[ -z "${HEALTH}" ]]; then
    docker logs "${HTTP_CID}" >"${HTTP_LOG}" 2>&1 || true
    tail -40 "${HTTP_LOG}"
    fail "HTTP/SSE: /health never responded within 40s"
fi

if ! grep -Eq '"status"\s*:\s*"(healthy|degraded)"' <<<"${HEALTH}"; then
    printf 'Body:\n%s\n' "${HEALTH}"
    fail "HTTP/SSE: /health body did not contain status=healthy|degraded"
fi

ok "HTTP/SSE: /health responded:"
printf '         %s\n' "${HEALTH}"

# ─── 4. Done ────────────────────────────────────────────────────────
cleanup
trap - EXIT
log "${GREEN}All smoke tests passed ✅${RESET}"
