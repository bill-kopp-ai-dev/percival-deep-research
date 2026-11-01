"""Reachable regressions for the Percival timeout incident."""

import asyncio
import sys

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_external_cancel_reaps_worker(monkeypatch):
    from percival_research.research_worker_client import run_research_worker

    spawned = asyncio.Event()
    processes = []
    real_spawn = asyncio.create_subprocess_exec

    async def spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        processes.append(process)
        spawned.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(
        run_research_worker("fixture", 30, [sys.executable, "-c", "import time; time.sleep(30)"])
    )
    await spawned.wait()
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        with pytest.raises(asyncio.CancelledError):
            await task
        assert processes[0].returncode is not None, "cancelled caller left a live worker"
    finally:
        if processes[0].returncode is None:
            processes[0].kill()
            await processes[0].wait()


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_cancel_shared_research(clean_app_state, monkeypatch):
    import percival_research.tools.deep_research as dr

    started, finish = asyncio.Event(), asyncio.Event()

    async def research(*args):
        started.set()
        await finish.wait()
        return "Research complete."

    monkeypatch.setattr(dr, "_do_deep_research", research)
    creator = asyncio.create_task(dr.deep_research("shared cancellation fixture"))
    await started.wait()
    waiter = asyncio.create_task(dr.deep_research("shared cancellation fixture"))
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    shared = dr._IN_FLIGHT["shared cancellation fixture"]
    finish.set()
    assert await creator == "Research complete."
    assert not shared.cancelled()
    assert not dr._IN_FLIGHT


@pytest.mark.asyncio
async def test_creator_cancel_during_admission_cleans_dedup(clean_app_state, monkeypatch):
    import percival_research.app as app
    import percival_research.tools.deep_research as dr
    from utils import RateLimiter

    limiter = RateLimiter(max_concurrent=1)
    await limiter.acquire()
    monkeypatch.setattr(app, "research_limiter", limiter)
    creator = asyncio.create_task(dr.deep_research("admission cancellation fixture"))
    await asyncio.sleep(0.01)
    shared = dr._IN_FLIGHT["admission cancellation fixture"]
    creator.cancel()
    with pytest.raises(asyncio.CancelledError):
        await creator
    try:
        assert "admission cancellation fixture" not in dr._IN_FLIGHT
        assert shared.done()
        assert limiter._pending == 1  # the test still owns its original permit
    finally:
        dr._IN_FLIGHT.clear()
        limiter.release()


@pytest.mark.asyncio
async def test_internal_timeout_is_an_mcp_error(clean_app_state, monkeypatch):
    import percival_research.tools.deep_research as dr
    from server import mcp

    async def timeout(*args):
        raise TimeoutError

    monkeypatch.setattr(dr, "run_research_worker", timeout)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "research_deep", {"query": "MCP timeout fixture"}, raise_on_error=False
        )
    assert result.is_error
    assert "internal limit" in result.content[0].text


@pytest.mark.asyncio
async def test_empty_research_does_not_create_successful_session(
    clean_app_state, mock_gpt_researcher, monkeypatch
):
    import percival_research.tools.deep_research as dr

    async def empty(*args):
        return [], [], []

    monkeypatch.setattr(dr, "run_research_worker", empty)
    result = await dr.deep_research("empty fixture")
    assert result.startswith("Error:")
    assert "research_id:" not in result
    assert not clean_app_state["registry"]._researchers


@pytest.mark.asyncio
async def test_report_has_internal_timeout(clean_app_state, mock_gpt_researcher, monkeypatch):
    import percival_research.tools.write_report as reports
    from percival_research.tools.deep_research import deep_research

    summary = await deep_research("report timeout fixture")
    research_id = summary.split("research_id: ")[1].splitlines()[0]

    async def timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(reports, "run_report_worker", timeout)
    result = await reports.write_report(research_id)
    assert result.startswith("Error:")
    assert "internal limit" in result
    # A report failure must not force a paid repeat of the successful research.
    assert clean_app_state["registry"].get_researcher(research_id)[0]
