"""Tool: get_research_sources — metadados das fontes."""

from percival_research.app import mcp
import percival_research.app as _app
from utils import (
    format_sources_for_response,
    format_sources_lines,
    handle_exception,
    new_correlation_id,
    validate_research_id,
    wrap_untrusted_content,
)


@mcp.tool("research_get_sources")
async def get_research_sources(research_id: str) -> str:
    """Returns detailed metadata for all sources consulted during a research session."""
    cid = new_correlation_id()
    if not validate_research_id(research_id):
        return f"Error: Invalid research_id. Provide a valid UUID. (correlation_id={cid})"

    success, researcher, error = _app.registry.get_researcher(research_id)
    if not success:
        msg = error.get("message", "Research session not found or expired.")
        return f"Error: {msg} (correlation_id={cid})"

    try:
        sources = researcher.get_research_sources()
        formatted = format_sources_for_response(sources)

        lines = [f"source_count: {len(formatted)}", ""]
        lines.extend(format_sources_lines(formatted))
        # N4 fix (rodada 4): `sources[].content` vem direto de páginas web
        # scrapeadas — wrap consistente com `get_research_context` e
        # `research://{topic}`. Sem isso, scraper malicioso injeta
        # instruções sem aviso no agente.
        return wrap_untrusted_content("\n".join(lines))
    except Exception as e:
        return handle_exception(e, "Get research sources", cid)