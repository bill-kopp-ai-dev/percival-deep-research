"""Client for the isolated upstream research worker.

The upstream `gpt-researcher` pipeline can absorb `CancelledError`, so an
in-process timeout does not stop the work. Running the pipeline in a child
process lets the parent enforce a hard wall-clock limit and kill the
worker when the deadline is exceeded.
"""

from __future__ import annotations

import asyncio
import json
import sys


async def run_research_worker(
    query: str,
    timeout_s: float,
    worker_command: list[str] | None = None,
) -> tuple[list, list, list[str]]:
    """Run upstream research in a killable process with a strict wall-clock limit.

    Raises:
        asyncio.TimeoutError: the worker exceeded `timeout_s` and was killed.
        RuntimeError: the worker failed or returned an invalid payload.
    """
    worker = await asyncio.create_subprocess_exec(
        *(worker_command or [sys.executable, "-m", "percival_research.research_worker"]),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    payload = json.dumps({"query": query}, ensure_ascii=False).encode("utf-8")
    try:
        stdout, _stderr = await asyncio.wait_for(worker.communicate(payload), timeout=timeout_s)
    except asyncio.TimeoutError:
        try:
            worker.kill()
        except ProcessLookupError:
            pass
        await worker.communicate()
        raise

    if worker.returncode != 0:
        raise RuntimeError(f"Research worker failed with exit status {worker.returncode}")
    try:
        result = json.loads(stdout)
        context = result["context"]
        sources = result["sources"]
        source_urls = result["source_urls"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError("Research worker returned an invalid result") from exc
    if (
        not isinstance(context, list)
        or not isinstance(sources, list)
        or not isinstance(source_urls, list)
    ):
        raise RuntimeError("Research worker returned an invalid result shape")
    return context, sources, source_urls
