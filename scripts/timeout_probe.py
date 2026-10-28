#!/usr/bin/env python3
"""Measure the effective research deadline against an internal fixture.

The fixture upstream never answers: it sleeps longer than the configured
`PERCIVAL_RESEARCH_TIMEOUT_S`. The probe asserts that `research_deep`
returns the timeout error within the deadline, that the response does not
claim success, and that the container exits cleanly afterwards.

This exercises the isolated-worker path: the parent kills the worker
process when the deadline expires.

Usage:
    scripts/timeout_probe.py --image percival-deep-research:stage2-candidate
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HARNESS_VERSION = "1.0.0"

INIT_REQ = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "timeout-probe", "version": "0.1.0"},
        },
    }
)
INITIALIZED = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
CALL_REQ = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "research_deep", "arguments": {"query": "fixture probe"}},
    }
)


class SlowUpstream(BaseHTTPRequestHandler):
    """Never answers within the deadline."""

    delay_s = 30.0

    def do_GET(self):  # noqa: N802 - http.server API
        time.sleep(self.delay_s)
        self._json({})

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length:
            self.rfile.read(length)
        time.sleep(self.delay_s)
        self._json({})

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: A002 - silence the default logging
        return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run_probe(image: str, timeout_s: int, upstream_delay_s: float) -> dict:
    port = _free_port()
    SlowUpstream.delay_s = upstream_delay_s
    server = ThreadingHTTPServer(("127.0.0.1", port), SlowUpstream)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    proc = subprocess.Popen(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "host",
            "-e",
            "INFERENCE_API_KEY=probe-not-a-real-key",
            "-e",
            f"INFERENCE_BASE_URL=http://127.0.0.1:{port}/v1",
            "-e",
            "INFERENCE_LLM=openai:probe-model",
            "-e",
            "RETRIEVER=searx",
            "-e",
            f"SEARX_URL=http://127.0.0.1:{port}/search",
            "-e",
            f"PERCIVAL_RESEARCH_TIMEOUT_S={timeout_s}",
            "-e",
            "MCP_TRANSPORT=stdio",
            "-e",
            "LOG_LEVEL=ERROR",
            image,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None and proc.stdout is not None

    responses: dict[int, dict] = {}

    def read_until(response_id: int, deadline: float) -> dict:
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("id") == response_id:
                responses[response_id] = message
                return message
        raise TimeoutError(f"no JSON-RPC response for id {response_id}")

    try:
        proc.stdin.write(INIT_REQ + "\n")
        proc.stdin.flush()
        read_until(1, time.monotonic() + 120)

        proc.stdin.write(INITIALIZED + "\n" + CALL_REQ + "\n")
        proc.stdin.flush()
        started = time.monotonic()
        call = read_until(2, time.monotonic() + timeout_s + 30)
        elapsed = time.monotonic() - started
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        server.shutdown()

    text = ""
    result = call.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            text = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
    return {
        "elapsed_s": round(elapsed, 3),
        "timeout_s": timeout_s,
        "exit_code": proc.returncode,
        "response": text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=False, help="image:tag to exercise")
    parser.add_argument("--timeout", type=int, default=2, help="PERCIVAL_RESEARCH_TIMEOUT_S")
    parser.add_argument("--upstream-delay", type=float, default=30.0)
    parser.add_argument("--max-elapsed", type=float, default=3.0)
    parser.add_argument("--harness-version", action="store_true", help="print the harness version")
    args = parser.parse_args()

    if args.harness_version:
        print(f"deep-research timeout probe {HARNESS_VERSION}")
        return 0
    if not args.image:
        parser.error("--image is required unless --harness-version is given")

    outcome = run_probe(args.image, args.timeout, args.upstream_delay)
    print(json.dumps(outcome, indent=2, ensure_ascii=False))

    response = outcome["response"]
    problems = []
    if "internal limit" not in response:
        problems.append("response does not report the internal limit")
    if "Research complete." in response:
        problems.append("response claims success although the deadline expired")
    if outcome["elapsed_s"] > args.max_elapsed:
        problems.append(f"elapsed {outcome['elapsed_s']}s exceeds the {args.max_elapsed}s budget")
    if outcome["exit_code"] not in (0, None):
        problems.append(f"container exited with {outcome['exit_code']}")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("timeout probe passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
