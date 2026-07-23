"""Tool: quick_search — busca rápida sem síntese."""

import asyncio
import sys
from contextlib import redirect_stdout

from gpt_researcher import GPTResearcher
from loguru import logger

from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    mcp,
    metrics,
)
import percival_research.app as _app
from utils import handle_exception, new_correlation_id, sanitize_query


@mcp.tool("research_quick_search")
async def quick_search(query: str) -> str:
    """Fast web search that returns raw result snippets without deep synthesis."""
    cid = new_correlation_id()
    try:
        query = sanitize_query(query)
    except ValueError as e:
        return f"Error: {str(e)} (correlation_id={cid})"

    logger.info(f"[{cid}] Starting quick search: {query!r}")

    # N1 fix (rodada 4): rate-limit assim como deep_research. Sem isso,
    # 100 calls paralelas disparam 100 GPTResearcher (~200MB cada) sem
    # back-pressure → exaustão de memória + rate-limit do retriever.
    try:
        await _app.research_limiter.acquire()
    except asyncio.TimeoutError:
        metrics.record_timeout("quick_search")
        logger.warning(f"[{cid}] quick_search rate limit acquire timeout")
        return (
            f"Error: Server is busy (concurrent research limit reached). "
            f"Try again in a few seconds. (correlation_id={cid})"
        )

    try:
        return await _do_quick_search(query, cid)
    finally:
        _app.research_limiter.release()


async def _do_quick_search(query: str, cid: str) -> str:
    """Corpo principal do quick_search, separado para garantir que
    `release()` seja sempre chamado mesmo em caso de exceção."""
    researcher = GPTResearcher(
        query=query,
        agent=UNIVERSAL_AGENT_NAME,
        role=_app._get_universal_agent_role(),  # dinâmico (audit rodada 2)
        verbose=False,
    )
    try:
        with redirect_stdout(sys.stderr):
            search_results = await researcher.quick_search(query=query)
    except Exception as e:
        metrics.record_error("quick_search")
        return handle_exception(e, "Quick search", cid)

    logger.info(f"[{cid}] Quick search complete. query={query!r}")

    result_count = len(search_results) if search_results else 0
    lines = [f"result_count: {result_count}", ""]

    if search_results:
        for i, result in enumerate(search_results, 1):
            snippet = str(result)
            lines.append(f"[Result {i}] {snippet}")
    else:
        lines.append("No results found.")

    return "\n".join(lines)