"""Tool: quick_search — busca rápida sem síntese."""

import sys
from contextlib import redirect_stdout

from gpt_researcher import GPTResearcher
from loguru import logger

from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    mcp,
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

    try:
        researcher = GPTResearcher(
            query=query,
            agent=UNIVERSAL_AGENT_NAME,
            role=_app._get_universal_agent_role(),  # dinâmico (audit rodada 2)
            verbose=False,
        )
        with redirect_stdout(sys.stderr):
            search_results = await researcher.quick_search(query=query)
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

    except Exception as e:
        return handle_exception(e, "Quick search", cid)