"""Run upstream operations in a process with a hard deadline and owned cleanup."""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import sys
import time
import uuid
from contextlib import suppress

import anyio
from fastmcp.server.dependencies import get_context
from loguru import logger

_PROGRESS_INTERVAL_S = 10
_SEARCH_EVENT = re.compile(
    rb"PERCIVAL_SEARCH backend=(duckduckgo|yahoo) outcome=(error|complete) "
    rb"(error_type=[A-Za-z][A-Za-z0-9_]{0,63}|results=[0-9]{1,6}) elapsed_ms=[0-9]{1,10}"
)

_STAGES = {
    "bootstrap",
    "construct",
    "planning",
    "search",
    "search_engine",
    "search_complete",
    "source_fetch",
    "scraping",
    "compression",
    "report",
    "complete",
}


class ProviderRejectedError(RuntimeError):
    """A permanent, sanitized inference error; retrying research cannot fix it."""

    def __init__(self, status: int):
        self.status_code = status
        reason = {
            400: "invalid provider request",
            401: "check provider credentials",
            402: "provider quota or billing limit reached",
            403: "provider access denied",
            404: "check provider base URL and model",
            405: "check provider base URL",
            413: "provider input size limit reached",
            422: "invalid provider parameters",
        }[status]
        super().__init__(f"Inference provider rejected request (HTTP {status}: {reason}).")


async def _report_progress(operation: str) -> None:
    """Keep progress-aware clients alive; the worker still owns a hard deadline.

    Progress is elapsed seconds, not a completion percentage. Never include
    queries or upstream output in these transport notifications.
    """
    try:
        context = get_context()
    except RuntimeError:
        return  # Worker calls outside an MCP request (e.g. resources/tests).
    started = time.monotonic()
    try:
        while True:
            await context.report_progress(
                progress=time.monotonic() - started, message=f"{operation} worker running"
            )
            await asyncio.sleep(_PROGRESS_INTERVAL_S)
    except Exception as exc:
        # Losing an optional progress channel must not leak a task or replay work.
        logger.warning("Worker progress unavailable: {}", type(exc).__name__)


async def _run_worker(payload: dict, timeout_s: float, command: list[str] | None = None) -> dict:
    worker_id = uuid.uuid4().hex[:12]
    operation = payload.get("operation", "research")
    worker = await asyncio.create_subprocess_exec(
        *(command or [sys.executable, "-m", "percival_research.research_worker"]),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    logger.info(
        "worker={} pid={} operation={} timeout_s={} started",
        worker_id,
        worker.pid,
        operation,
        timeout_s,
    )
    io = asyncio.create_task(worker.communicate(json.dumps(payload, ensure_ascii=False).encode()))
    progress = asyncio.create_task(_report_progress(operation))
    outcome = "completed"
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(io), timeout=timeout_s)
    except BaseException:
        outcome = "cancelled" if asyncio.current_task().cancelling() else "timeout"
        # Killing only `communicate` or the Docker attach does not stop upstream.
        # Kill the owned process group, then drain/reap under a cancellation shield.
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        with anyio.CancelScope(shield=True):
            stdout, stderr = await asyncio.wait_for(asyncio.shield(io), timeout=5)
        raise
    finally:
        progress.cancel()
        with anyio.CancelScope(shield=True), suppress(asyncio.CancelledError):
            await progress
        # Only our bounded, structured stage markers may leave the private pipe.
        # Never log upstream stderr: it can contain queries, keys or HTTP bodies.
        stage = "bootstrap"
        if io.done() and not io.cancelled() and io.exception() is None:
            for line in io.result()[1].splitlines():
                if line.startswith(b"PERCIVAL_STAGE "):
                    value = line.removeprefix(b"PERCIVAL_STAGE ").decode("ascii", errors="ignore")
                    if value in _STAGES:
                        stage = value
                elif _SEARCH_EVENT.fullmatch(line):
                    logger.info("worker={} {}", worker_id, line.decode("ascii"))
                elif re.fullmatch(rb"PERCIVAL_FAILURE error_type=[A-Za-z][A-Za-z0-9_]{0,63}", line):
                    logger.info("worker={} {}", worker_id, line.decode("ascii"))
        if outcome == "completed" and worker.returncode not in (None, 0):
            outcome = "failed"
        logger.info(
            "worker={} pid={} operation={} outcome={} last_stage={} reaped={}",
            worker_id,
            worker.pid,
            operation,
            outcome,
            stage,
            worker.returncode is not None,
        )

    if worker.returncode != 0:
        raise RuntimeError(
            f"Research worker failed with exit status {worker.returncode} (stage={stage})"
        )
    try:
        result = json.loads(stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Research worker returned an invalid result") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Research worker returned an invalid result shape")
    error = result.get("error")
    if (
        isinstance(error, dict)
        and error.get("kind") == "provider_rejected"
        and type(error.get("status")) is int
        and error["status"] in (400, 401, 402, 403, 404, 405, 413, 422)
    ):
        raise ProviderRejectedError(error["status"])
    return result


def validate_research_data(context, sources, source_urls) -> None:
    """Reject empty/invalid upstream data before claiming a successful session."""
    if (
        not isinstance(context, (list, str))
        or not context
        or not isinstance(sources, list)
        or not sources
        or any(not isinstance(source, dict) for source in sources)
        or not isinstance(source_urls, list)
        or not source_urls
        or any(
            not isinstance(url, str) or not url.startswith(("https://", "http://"))
            for url in source_urls
        )
    ):
        raise RuntimeError("Research worker returned empty or invalid research data")


async def run_research_worker(
    query: str,
    timeout_s: float,
    worker_command: list[str] | None = None,
) -> tuple[list | str, list, list[str]]:
    result = await _run_worker({"query": query}, timeout_s, worker_command)
    try:
        context, sources, source_urls = result["context"], result["sources"], result["source_urls"]
    except KeyError as exc:
        raise RuntimeError("Research worker returned an invalid result") from exc
    validate_research_data(context, sources, source_urls)
    return context, sources, source_urls


async def run_report_worker(
    query: str,
    context: list | str,
    sources: list,
    source_urls: list[str],
    custom_prompt: str | None,
    timeout_s: float,
) -> str:
    result = await _run_worker(
        {
            "operation": "report",
            "query": query,
            "context": context,
            "sources": sources,
            "source_urls": source_urls,
            "custom_prompt": custom_prompt,
        },
        timeout_s,
    )
    report = result.get("report")
    if not isinstance(report, str) or not report.strip():
        raise RuntimeError("Research worker returned an empty or invalid report")
    # Some OpenAI-compatible providers prepend auxiliary reasoning to content.
    # Strip only leading provider envelopes, never literal tags in the report.
    report = report.lstrip()
    while report.lower().startswith("<think>"):
        end = report.lower().find("</think>")
        if end == -1:
            raise RuntimeError("Inference provider returned an incomplete report")
        report = report[end + len("</think>") :].lstrip()
    if not report.strip():
        raise RuntimeError("Inference provider returned no final report")
    return report
