"""Prompt: research_query."""

from percival_research.app import mcp
from utils import create_research_prompt


@mcp.prompt("research_query")
def research_query(
    topic: str,
    goal: str = "Sintetize os melhores resultados",
    report_format: str = "research_report",
) -> str:
    """Renderiza um prompt de research orientado a MCP (v2.2+).

    Args:
        topic: Tópico da pesquisa (sanitizado via `sanitize_topic`).
        goal: Objetivo livre do agente, em linguagem natural.
        report_format: Formato do report final (research_report, summary, etc.).

    Returns:
        Texto do prompt renderizado; inclui cabeçalho "Please research..."
        e as instruções operacionais para usar deep_research/get_research_*
        via MCP. Se algum argumento for inválido, retorna string
        ``[VALIDATION ERROR: ...]`` para que o caller saiba.
    """
    try:
        return create_research_prompt(topic, goal, report_format)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"