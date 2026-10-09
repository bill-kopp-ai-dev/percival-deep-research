#!/usr/bin/env python3
"""Drive a FastMCP stdio container through ``docker run -i`` keeping the
pipe open across initialize, notifications/initialized, and tools/list.

Returns the server's stdout on success; exits non-zero if the server
exits prematurely or the output does not contain a tool name listed
on the command line.

Designed to be invoked from ``scripts/docker_smoke_test.sh``; the
``IMAGE_TAG`` and ``DUMMY_KEY`` environment variables and the
``--expected-tool`` CLI flag are passed in by the shell harness.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

INIT_REQ = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize",'
    '"params":{"protocolVersion":"2024-11-05","capabilities":{},'
    '"clientInfo":{"name":"smoke-test","version":"0.0.0"}}}'
)
INITIALIZED = '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
TOOLS_REQ = '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image-tag",
        required=True,
        help="image:tag to launch via docker run",
    )
    parser.add_argument(
        "--expected-tool",
        action="append",
        required=True,
        help="tool name that must appear in the server's response",
    )
    parser.add_argument(
        "--dummy-key",
        default="smoke-test-dummy-key-not-real",
        help="placeholder INFERENCE_API_KEY value",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=20.0,
        help="seconds to wait for the server to exit after closing stdin",
    )
    args = parser.parse_args()

    proc = subprocess.Popen(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "-e",
            f"INFERENCE_API_KEY={args.dummy_key}",
            "-e",
            "INFERENCE_BASE_URL=https://api.openai.com/v1",
            "-e",
            "INFERENCE_LLM=openai:gpt-4o-mini",
            "-e",
            "RETRIEVER=duckduckgo",
            "-e",
            "MCP_TRANSPORT=stdio",
            "-e",
            "LOG_LEVEL=WARNING",
            args.image_tag,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert proc.stdin is not None
    for line in (INIT_REQ, INITIALIZED, TOOLS_REQ):
        proc.stdin.write(line + "\n")
        proc.stdin.flush()
    proc.stdin.close()
    output_chunks: list[str] = []
    deadline = time.monotonic() + args.read_timeout
    while True:
        chunk = proc.stdout.read(1)
        if not chunk:
            break
        output_chunks.append(chunk)
        if proc.poll() is not None and time.monotonic() > deadline:
            break
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    output = "".join(output_chunks)
    if proc.returncode and proc.returncode != 0:
        sys.stderr.write(f"server exited {proc.returncode}\n")
        sys.stderr.write(output)
        return 2
    missing = [tool for tool in args.expected_tool if tool not in output]
    if missing:
        sys.stderr.write("server response (first 1000 chars):\n")
        sys.stderr.write(output[:1000] + "\n")
        sys.stderr.write(f"missing tools: {missing}\n")
        return 3
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
