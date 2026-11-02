#!/usr/bin/env python3
"""Exercise the real image through Percival's broker and wrappers, without real keys.

The disposable container uses a local OpenAI/SearX/HTML fixture. Nothing is
installed in either manager. Success covers a >30s call, getters, isolated
report and cache; timeout/cancel modes prove cleanup and subsequent reads.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from mcp.client.streamable_http import streamable_http_client


class Upstream(BaseHTTPRequestHandler):
    calls = 0
    embeddings = 0
    delay_s = 31.0
    started = threading.Event()

    def log_message(self, *args):
        pass

    def respond(self, payload, mime="application/json"):
        body = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):  # noqa: N802
        url = f"http://127.0.0.1:{self.server.server_port}/source"
        if self.path.startswith("/search"):
            self.respond(
                {"results": [{"url": url, "title": "Fixture", "content": "Fixture evidence"}]}
            )
        else:
            # Force the original compressor's embedding path (>8000 chars).
            self.respond(
                "<html><title>Fixture source</title><body><p>"
                + "Fixture evidence supports bounded reproducible research. " * 240
                + "</p></body></html>",
                "text/html",
            )

    def do_POST(self):  # noqa: N802
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "embeddings" in self.path:
            Upstream.embeddings += 1
            self.send_error(501)
            return
        Upstream.calls += 1
        number = Upstream.calls
        Upstream.started.set()
        if number == 1:
            time.sleep(Upstream.delay_s)
        content = (
            '["fixture research"]'
            if number == 1
            else "<think>fixture auxiliary provider text</think>\n# Fixture report\n\nEvidence supports bounded research. "
            f"[Fixture](http://127.0.0.1:{self.server.server_port}/source). "
            "Limitation: synthetic fixture only."
        )
        base = {"id": "fixture", "created": 1, "model": "fixture"}
        if request.get("stream"):
            first = {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
            last = {"index": 0, "delta": {}, "finish_reason": "stop"}
            chunks = [
                {**base, "object": "chat.completion.chunk", "choices": [choice]}
                for choice in (first, last)
            ]
            self.respond(
                "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n",
                "text/event-stream",
            )
        else:
            choice = {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
            self.respond(
                {
                    **base,
                    "object": "chat.completion",
                    "choices": [choice],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
                }
            )


def workers(container):
    result = subprocess.run(
        ["docker", "top", container, "-eo", "pid,args"], capture_output=True, text=True, check=True
    )
    return sum(
        "-m percival_research.research_worker" in line for line in result.stdout.splitlines()
    )


async def exercise(port, mode, container):
    from nanobot.agent.tools.mcp import MCPToolWrapper
    from nanobot.agent.tools.mcp_session import CancellableClientSession

    async with httpx.AsyncClient(timeout=190, trust_env=False) as http:
        async with streamable_http_client(
            f"http://127.0.0.1:{port}/mcp/fixture", http_client=http
        ) as (read, write, _):
            async with CancellableClientSession(read, write) as session:
                await session.initialize()
                definitions = (await session.list_tools()).tools
                wrappers = {
                    tool.name: MCPToolWrapper(session, "fixture", tool, tool_timeout=180)
                    for tool in definitions
                }
                started = time.monotonic()
                call = asyncio.create_task(
                    wrappers["research_deep"].execute(query="fixture research")
                )
                if mode == "cancel":
                    assert await asyncio.to_thread(Upstream.started.wait, 20), (
                        "worker did not reach fixture"
                    )
                    call.cancel()
                    try:
                        await call
                    except asyncio.CancelledError:
                        pass
                    result = "cancelled"
                else:
                    result = await call
                elapsed = time.monotonic() - started
                if mode == "success":
                    assert "Research complete." in result and not getattr(
                        result, "is_error", False
                    ), result
                    research_id = result.split("research_id: ")[1].splitlines()[0]
                    context = await wrappers["research_get_context"].execute(
                        research_id=research_id
                    )
                    sources = await wrappers["research_get_sources"].execute(
                        research_id=research_id
                    )
                    report = await wrappers["research_write_report"].execute(
                        research_id=research_id
                    )
                    assert "SECURITY WARNING" in context and "source_count: 1" in sources
                    assert "# Fixture report" in report and "/source" in report, report
                    assert (
                        "<think>" not in report and "fixture auxiliary provider text" not in report
                    )
                    quick = await wrappers["research_quick_search"].execute(query="fixture search")
                    assert "result_count: 1" in quick and "/source" in quick, quick
                    cache = await session.read_resource("research://fixture%20research")
                    assert "SECURITY WARNING" in cache.contents[0].text
                    assert Upstream.calls == 2, "cache/getters started extra inference"
                elif mode == "timeout":
                    assert getattr(result, "is_error", False) and "internal limit" in result, result
                for _ in range(50):
                    if not workers(container):
                        break
                    await asyncio.sleep(0.1)
                assert workers(container) == 0, "orphan worker after operation"
                # A safe request must work after cancellation/timeout, without replay.
                check = await wrappers["research_get_context"].execute(
                    research_id=str(uuid.uuid4())
                )
                assert getattr(check, "is_error", False) and "not found" in check
                assert Upstream.embeddings == 0, "child process lost the compressor patch"
                print(
                    json.dumps(
                        {
                            "mode": mode,
                            "elapsed_s": round(elapsed, 3),
                            "inference_calls": Upstream.calls,
                            "embedding_calls": Upstream.embeddings,
                            "workers_remaining": 0,
                            "passed": True,
                            "tools_exercised": 5 if mode == "success" else 2,
                        }
                    ),
                    flush=True,
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--percival-checkout", required=True, type=Path)
    parser.add_argument("--mode", choices=("success", "timeout", "cancel"), default="success")
    parser.add_argument("--delay", type=float, default=31)
    args = parser.parse_args()
    sys.path.insert(0, str(args.percival_checkout))
    broker = importlib.import_module("nanobot.mcp_docker.broker")
    contracts = importlib.import_module("nanobot.mcp_docker.contracts")
    Upstream.delay_s = args.delay if args.mode == "success" else 30
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{upstream.server_port}"
    container = "percival-dr-pipeline-probe-" + uuid.uuid4().hex[:12]
    env = {
        "INFERENCE_API_KEY": "fixture-not-real",
        "OPENAI_API_KEY": "fixture-not-real",
        "INFERENCE_BASE_URL": base + "/v1",
        "OPENAI_BASE_URL": base + "/v1",
        "INFERENCE_LLM": "openai:fixture",
        "FAST_LLM": "openai:fixture",
        "SMART_LLM": "openai:fixture",
        "STRATEGIC_LLM": "openai:fixture",
        "RETRIEVER": "searx",
        "SEARX_URL": base,
        "MCP_TRANSPORT": "stdio",
        "PERCIVAL_RESEARCH_TIMEOUT_S": "3" if args.mode == "timeout" else "90",
    }
    command = [
        "docker",
        "run",
        "-d",
        "-i",
        "--init",
        "--pull=never",
        "--network=host",
        "--name",
        container,
        "--label",
        "io.percival.fixture=deep-research-pipeline",
    ]
    for key, value in env.items():
        command += ["-e", f"{key}={value}"]
    subprocess.run([*command, args.image], check=True, capture_output=True)
    try:
        # Only this disposable fixture is routed through the real broker code.
        broker._name = lambda _: container
        broker._running = lambda _: True
        broker.Handler.authorized = lambda _: True
        server = broker.ManagedServer(
            "fixture",
            contracts.DockerImageSource(
                type="local-image",
                reference=args.image,
            ),
            contracts.DockerHostConfig(mounts=[], network="none"),
        )
        broker._STORE["fixture"] = server
        server.tools = broker._discover("fixture")
        http = broker.DrainingThreadingHTTPServer(("127.0.0.1", 0), broker.Handler)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            asyncio.run(exercise(http.server_port, args.mode, container))
        finally:
            http.shutdown()
            http.server_close()
    finally:
        subprocess.run(
            ["docker", "stop", "--time", "5", container], check=True, capture_output=True
        )
        subprocess.run(["docker", "rm", container], check=True, capture_output=True)
        upstream.shutdown()


if __name__ == "__main__":
    main()
