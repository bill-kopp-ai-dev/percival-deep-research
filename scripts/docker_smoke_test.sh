#!/usr/bin/env bash
# End-to-end smoke test for the candidate image's stdio and HTTP contracts.
#
# The image is retained for rollback. Only the uniquely named HTTP fixture
# container is removed by this script.

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

IMAGE_TAG="${IMAGE_TAG:-percival-deep-research:smoke}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"
SOURCE_VERSION="${SOURCE_VERSION:-$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')}"
SOURCE_REVISION="${SOURCE_REVISION:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
DUMMY_KEY="${DUMMY_KEY:-smoke-test-dummy-key-not-real}"
HTTP_NAME="percival-deep-research-f1-smoke-$$"
HTTP_CID=""
STDIO_LOG="/tmp/percival-deep-research-stdio-$$.log"
HTTP_LOG="/tmp/percival-deep-research-http-$$.log"

if [[ -t 1 ]]; then
    BLUE='\033[1;34m'; GREEN='\033[1;32m'; RED='\033[1;31m'; RESET='\033[0m'
else
    BLUE=''; GREEN=''; RED=''; RESET=''
fi

log()  { printf "${BLUE}[smoke]${RESET} %s\n" "$*"; }
ok()   { printf "${GREEN}[smoke OK]${RESET} %s\n" "$*"; }
fail() { printf "${RED}[smoke FAIL]${RESET} %s\n" "$*" >&2; exit 1; }

cleanup() {
    if [[ -n "${HTTP_CID}" ]]; then
        docker rm -f "${HTTP_CID}" >/dev/null 2>&1 || true
    fi
    rm -f "${STDIO_LOG}" "${HTTP_LOG}"
}
trap cleanup EXIT

log "Building ${IMAGE_TAG} for linux/amd64 (revision=${SOURCE_REVISION})..."
docker build \
    --platform linux/amd64 \
    --file "${DOCKERFILE}" \
    --build-arg "VERSION=${SOURCE_VERSION}" \
    --build-arg "GIT_SHA=${SOURCE_REVISION}" \
    --tag "${IMAGE_TAG}" \
    --label "org.opencontainers.image.revision=${SOURCE_REVISION}" \
    --label "smoke.test=percival-deep-research" \
    .
ok "Candidate image built and retained: ${IMAGE_TAG}."

# The image is consumed in stdio mode by default, so it must not carry an
# HTTP healthcheck. Tini in the image is the sole init for both transports.
IMAGE_HEALTHCHECK=$(docker image inspect --format '{{json .Config.Healthcheck}}' "${IMAGE_TAG}")
[[ "${IMAGE_HEALTHCHECK}" == "null" ]] || fail "stdio image has a healthcheck: ${IMAGE_HEALTHCHECK}"
IMAGE_ENTRYPOINT=$(docker image inspect --format '{{json .Config.Entrypoint}}' "${IMAGE_TAG}")
[[ "${IMAGE_ENTRYPOINT}" == '["/usr/bin/tini","--","percival-deep-research"]' ]] \
    || fail "expected tini as the single image init, got ${IMAGE_ENTRYPOINT}"
ok "Image defaults have no HTTP healthcheck and use one tini init."

log "STDIO smoke: initialize and tools/list without a TTY or published port..."
# FastMCP 3.4+ answers tools/list only when the client keeps the pipe open
# after initialize/notifications/initialized. scripts/docker_stdio_probe.py
# runs the request sequence in a Python coprocess so the container's stdin
# stays alive long enough for both responses to arrive.
STDIO_RES=$(python3 "$(dirname -- "${BASH_SOURCE[0]}")/docker_stdio_probe.py" \
    --image-tag "${IMAGE_TAG}" --dummy-key "${DUMMY_KEY}" \
    --expected-tool research_deep \
    --expected-tool research_quick_search \
    --expected-tool research_get_context \
    --expected-tool research_get_sources \
    --expected-tool research_write_report) \
    || { printf '%s\n' "$(tail -40 "${STDIO_LOG}")"; fail "stdio container exited non-zero"; }

[[ "${STDIO_RES}" == *'"jsonrpc"'* ]] || {
    printf 'STDIO response (first 1000 chars):\n%.1000s\n' "${STDIO_RES}"
    fail "stdio response missing jsonrpc envelope"
}
ok "STDIO initialize and all five tools passed over JSON-RPC."

log "HTTP/SSE smoke: start isolated fixture on a loopback-only ephemeral port..."
HTTP_CID=$(docker run -d \
    --name "${HTTP_NAME}" \
    -p 127.0.0.1::8000 \
    --health-cmd 'python -c "import http.client,sys; c=http.client.HTTPConnection(\"127.0.0.1\",8000,timeout=3); c.request(\"GET\",\"/health\"); s=c.getresponse().status; sys.exit(0 if s in (200,503) else 1)"' \
    --health-interval=2s \
    --health-timeout=5s \
    --health-retries=3 \
    --health-start-period=5s \
    -e INFERENCE_API_KEY="${DUMMY_KEY}" \
    -e INFERENCE_BASE_URL="https://api.openai.com/v1" \
    -e INFERENCE_LLM="openai:gpt-4o-mini" \
    -e RETRIEVER=duckduckgo \
    -e MCP_TRANSPORT=sse \
    -e MCP_HOST=0.0.0.0 \
    -e PORT=8000 \
    -e LOG_LEVEL=WARNING \
    "${IMAGE_TAG}")

HTTP_PORT=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}' "${HTTP_CID}")
HTTP_BIND=$(docker port "${HTTP_CID}" 8000/tcp)
[[ "${HTTP_BIND}" == "127.0.0.1:${HTTP_PORT}" ]] || fail "HTTP fixture is not loopback-only: ${HTTP_BIND}"
HTTP_PID1=$(docker inspect --format '{{.Path}}' "${HTTP_CID}")
HTTP_INIT=$(docker inspect --format '{{.HostConfig.Init}}' "${HTTP_CID}")
[[ "${HTTP_PID1}" == "/usr/bin/tini" && "${HTTP_INIT}" != "true" ]] \
    || fail "expected exactly one init (image tini), Path=${HTTP_PID1}, HostConfig.Init=${HTTP_INIT}"

HEALTH=""
for _ in {1..40}; do
    if HEALTH=$(curl -fsS "http://127.0.0.1:${HTTP_PORT}/health" 2>/dev/null); then
        break
    fi
    sleep 1
done
if [[ -z "${HEALTH}" ]]; then
    docker logs "${HTTP_CID}" >"${HTTP_LOG}" 2>&1 || true
    printf '%s\n' "$(tail -40 "${HTTP_LOG}")"
    fail "HTTP /health did not respond within 40s"
fi
[[ "${HEALTH}" == *'"status"'* ]] || fail "unexpected /health body: ${HEALTH}"

HEALTH_STATUS=""
for _ in {1..20}; do
    HEALTH_STATUS=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${HTTP_CID}")
    [[ "${HEALTH_STATUS}" == "healthy" ]] && break
    sleep 1
done
[[ "${HEALTH_STATUS}" == "healthy" ]] || fail "HTTP liveness probe status: ${HEALTH_STATUS}"
ok "HTTP /health responded on loopback (${HEALTH_STATUS}; body=${HEALTH})."

docker stop --time 10 "${HTTP_CID}" >/dev/null
EXIT_CODE=$(docker inspect --format '{{.State.ExitCode}}' "${HTTP_CID}")
[[ "${EXIT_CODE}" != "137" ]] || fail "HTTP container required SIGKILL; graceful stop timed out"
ok "SIGTERM reached the HTTP process through the single tini init (exit=${EXIT_CODE})."

log "All Deep Research F1 smoke checks passed."
