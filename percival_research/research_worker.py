"""Isolated process for upstream research, terminated by the parent on timeout."""

# Runtime environment must load before importing the upstream package.
# ruff: noqa: I001

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import redirect_stdout

import runtime_env as _runtime_env  # noqa: F401, I001 -- load env before upstream imports
from gpt_researcher import GPTResearcher
from percival_research.app import UNIVERSAL_AGENT_NAME, _get_universal_agent_role


async def _research(query: str) -> dict:
    researcher = GPTResearcher(
        query=query,
        agent=UNIVERSAL_AGENT_NAME,
        role=_get_universal_agent_role(),
        verbose=False,
    )
    with redirect_stdout(sys.stderr):
        await researcher.conduct_research()
    return {
        "context": researcher.get_research_context(),
        "sources": researcher.get_research_sources() or [],
        "source_urls": researcher.get_source_urls() or [],
    }


def main() -> int:
    try:
        request = json.loads(sys.stdin.buffer.read())
        result = asyncio.run(_research(request["query"]))
        sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
        return 0
    except Exception:
        # Do not serialize exception text: upstream errors may include request
        # context. The parent emits only a generic worker failure to the MCP.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
