"""Prompt: research_query."""

from percival_research.app import mcp
from utils import create_research_prompt


@mcp.prompt()
def research_query(topic: str, goal: str, report_format: str = "research_report") -> str:
    """..."""
    try:
        return create_research_prompt(topic, goal, report_format)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"