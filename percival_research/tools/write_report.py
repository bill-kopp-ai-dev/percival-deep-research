"""Tool: write_report — gera relatório estruturado de uma sessão de pesquisa."""

import sys
from contextlib import redirect_stdout

from loguru import logger

from percival_research.app import mcp
import percival_research.app as _app
from utils import (
    handle_exception,
    new_correlation_id,
    sanitize_prompt,
    validate_research_id,
)


@mcp.tool("research_write_report")
async def write_report(research_id: str, custom_prompt: str | None = None) -> str:
    """Generates a structured Markdown report from an existing research session."""
    cid = new_correlation_id()
    if not validate_research_id(research_id):
        return f"Error: Invalid research_id. Provide a valid UUID obtained from deep_research. (correlation_id={cid})"

    if custom_prompt is not None:
        try:
            custom_prompt = sanitize_prompt(custom_prompt)
        except ValueError as e:
            return f"Error: Invalid custom_prompt: {str(e)} (correlation_id={cid})"

    success, researcher, error = _app.registry.get_researcher(research_id)
    if not success:
        msg = error.get("message", "Research session not found or expired.")
        return f"Error: {msg} (correlation_id={cid})"

    logger.info(f"[{cid}] Generating report for ID: {research_id}")

    try:
        with redirect_stdout(sys.stderr):
            report = await researcher.write_report(custom_prompt=custom_prompt)

        lines = ["", report]
        return "\n".join(lines)

    except Exception as e:
        # Em caso de erro, evicta o researcher para liberar recursos.
        try:
            _app.registry.evict_researcher(research_id)
        except Exception:
            pass
        return handle_exception(e, "Report generation", cid)