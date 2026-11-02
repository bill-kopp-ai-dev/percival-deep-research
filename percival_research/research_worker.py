"""Isolated process for upstream research, terminated by the parent on timeout."""

# Runtime environment must load before importing the upstream package.
# ruff: noqa: I001

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import redirect_stdout

import runtime_env as _runtime_env  # noqa: F401, I001 -- load env before upstream imports
from gpt_researcher import GPTResearcher
from percival_research.app import UNIVERSAL_AGENT_NAME, _get_universal_agent_role
from percival_research.patches import apply_compressor_patch
from percival_research.retrievers.bounded_duckduckgo import install_bounded_retrievers


def _stage(name: str) -> None:
    print(f"PERCIVAL_STAGE {name}", file=sys.stderr, flush=True)


class _ResearchStages(logging.Handler):
    """Translate upstream progress into an allowlisted, content-free diagnostic."""

    def emit(self, record):
        message = record.getMessage()
        for marker, stage in (
            ("Scraped data size", "source_fetch"),
            ("Planning", "planning"),
            ("outline planned", "planning"),
            ("search results", "search"),
            ("web search", "search"),
            ("Scraping", "scraping"),
            ("scraping", "scraping"),
            ("Compress", "compression"),
            ("compress", "compression"),
        ):
            if marker in message:
                _stage(stage)
                break


async def _research(query: str, request: dict | None = None) -> dict:
    request = request or {}
    _stage("bootstrap")
    if not apply_compressor_patch():
        raise RuntimeError("Required compressor patch is incompatible")
    stages = _ResearchStages()
    logging.getLogger("research").addHandler(stages)
    logging.getLogger("research").setLevel(logging.INFO)
    _stage("construct")
    researcher = GPTResearcher(
        query=query,
        agent=UNIVERSAL_AGENT_NAME,
        role=_get_universal_agent_role(),
        verbose=False,
        context=request.get("context"),
    )
    install_bounded_retrievers(researcher)
    if request.get("operation") == "report":
        researcher.research_sources = request["sources"]
        researcher.visited_urls = set(request["source_urls"])
        _stage("report")
        report = await researcher.write_report(custom_prompt=request.get("custom_prompt"))
        _stage("complete")
        return {"report": report}
    _stage("planning")
    await researcher.conduct_research()
    _stage("complete")
    return {
        "context": researcher.get_research_context(),
        "sources": researcher.get_research_sources() or [],
        "source_urls": researcher.get_source_urls() or [],
    }


def main() -> int:
    try:
        request = json.loads(sys.stdin.buffer.read())
        # Constructors and getters can print too, not only conduct_research.
        with redirect_stdout(sys.stderr):
            result = asyncio.run(_research(request["query"], request))
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        # Do not serialize exception text: upstream errors may include request
        # context. The parent emits only a generic worker failure to the MCP.
        print(f"PERCIVAL_FAILURE error_type={type(exc).__name__}", file=sys.stderr, flush=True)
        status = getattr(exc, "status_code", None)
        if status in (400, 401, 402, 403, 404, 405, 413, 422):
            # Only allowlisted metadata crosses the private worker boundary.
            sys.stdout.write(json.dumps({"error": {"kind": "provider_rejected", "status": status}}))
            return 0
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
