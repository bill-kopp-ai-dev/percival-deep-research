"""Reachable regressions for the Percival timeout incident."""

import asyncio
import json
import sys

import pytest
from fastmcp import Client, FastMCP


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
async def test_worker_sends_progress_over_mcp_and_stops_after_completion(monkeypatch):
    import percival_research.research_worker_client as workers

    monkeypatch.setattr(workers, "_PROGRESS_INTERVAL_S", 0.03)
    fixture = FastMCP("worker-progress-fixture")
    payload = {
        "context": "Evidence",
        "sources": [{"url": "https://fixture.example"}],
        "source_urls": ["https://fixture.example"],
    }

    @fixture.tool
    async def run() -> str:
        await workers.run_research_worker(
            "fixture",
            2,
            [sys.executable, "-c", f"import time; time.sleep(0.2); print({json.dumps(payload)!r})"],
        )
        return "complete"

    progress = []

    async def receive(value, total, message):
        progress.append((value, total, message))

    async with Client(fixture, progress_handler=receive) as client:
        result = await client.call_tool("run", {})
        assert not result.is_error
        assert len(progress) >= 2
        count = len(progress)
        await asyncio.sleep(0.08)
        assert len(progress) == count, "progress task leaked after completion"
    assert all(
        total is None and message == "research worker running" for _, total, message in progress
    )
    assert progress[-1][0] > progress[0][0]


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


@pytest.mark.asyncio
async def test_provider_quota_failure_is_explicit_and_does_not_create_session(
    clean_app_state, monkeypatch
):
    import percival_research.tools.deep_research as dr
    from percival_research.research_worker_client import ProviderRejectedError, run_research_worker

    async def rejected(*args):
        return await run_research_worker(
            "fixture",
            2,
            [
                sys.executable,
                "-c",
                ('print(\'{"error":{"kind":"provider_rejected","status":402}}\')'),
            ],
        )

    monkeypatch.setattr(dr, "run_research_worker", rejected)
    result = await dr.deep_research("quota fixture")
    assert "HTTP 402" in result and "quota" in result
    assert "research_id:" not in result
    assert not clean_app_state["registry"]._researchers
    assert ProviderRejectedError(404).status_code == 404


@pytest.mark.asyncio
async def test_permanent_provider_failure_is_not_retried_by_upstream(monkeypatch):
    import gpt_researcher.actions.query_processing as planner
    import gpt_researcher.utils.llm as llm
    import httpx
    from openai import APIStatusError

    request = httpx.Request("POST", "https://fixture.example/v1/chat/completions")
    error = APIStatusError(
        "private provider response", response=httpx.Response(402, request=request), body=None
    )
    calls = []

    class RejectedProvider:
        async def get_chat_response(self, *args, **kwargs):
            calls.append("provider")
            raise error

    monkeypatch.setattr(llm, "get_llm", lambda *args, **kwargs: RejectedProvider())
    with pytest.raises(APIStatusError):
        await llm.create_chat_completion(messages=[], model="fixture", llm_provider="openai")
    assert calls == ["provider"]

    async def rejected(*args, **kwargs):
        calls.append("planner")
        raise error

    from types import SimpleNamespace

    monkeypatch.setattr(planner, "create_chat_completion", rejected)
    cfg = SimpleNamespace(
        max_iterations=1,
        strategic_llm_model="fixture",
        strategic_llm_provider="openai",
        llm_kwargs={},
    )
    with pytest.raises(APIStatusError):
        await planner.generate_sub_queries("fixture", "", "research_report", [], cfg)
    assert calls == ["provider", "planner"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("# Report\n\nEvidence.", "# Report\n\nEvidence."),
        (" \n<think>auxiliary provider text</think>\n# Report", "# Report"),
        ("<THINK>one</THINK><think>two</think>\n# Report", "# Report"),
        (
            "# XML examples\n\n```xml\n<think>literal</think>\n```",
            "# XML examples\n\n```xml\n<think>literal</think>\n```",
        ),
    ],
)
async def test_report_worker_returns_final_markdown_without_leading_auxiliary_blocks(
    monkeypatch, raw, expected
):
    import percival_research.research_worker_client as workers

    async def response(*args):
        return {"report": raw}

    monkeypatch.setattr(workers, "_run_worker", response)
    assert await workers.run_report_worker("fixture", "context", [], [], None, 2) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["<think>unfinished", "<think>auxiliary only</think>\n"])
async def test_report_worker_rejects_auxiliary_text_without_a_final_answer(monkeypatch, raw):
    import percival_research.research_worker_client as workers

    async def response(*args):
        return {"report": raw}

    monkeypatch.setattr(workers, "_run_worker", response)
    with pytest.raises(RuntimeError, match="report"):
        await workers.run_report_worker("fixture", "context", [], [], None, 2)
