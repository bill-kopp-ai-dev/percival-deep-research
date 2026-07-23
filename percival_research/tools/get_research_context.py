"""Tool: get_research_context — texto sintetizado do contexto."""

from percival_research.app import mcp
import percival_research.app as _app
from utils import (
    handle_exception,
    new_correlation_id,
    validate_research_id,
    wrap_untrusted_content,
)


@mcp.tool("research_get_context")
async def get_research_context(research_id: str) -> str:
    """Returns the raw synthesized context text from an existing research session."""
    cid = new_correlation_id()
    if not validate_research_id(research_id):
        return f"Error: Invalid research_id. Provide a valid UUID. (correlation_id={cid})"

    success, researcher, error = _app.registry.get_researcher(research_id)
    if not success:
        msg = error.get("message", "Research session not found or expired.")
        return f"Error: {msg} (correlation_id={cid})"

    try:
        return wrap_untrusted_content(researcher.get_research_context())
    except Exception as e:
        return handle_exception(e, "Get research context", cid)