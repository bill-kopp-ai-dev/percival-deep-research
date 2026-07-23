"""Prompts (primitive) — v2.3.0.

Quatro prompts cobrem os workflows canônicos do MCP server:

1. ``research_query`` — workflow completo (deep_research + write_report).
2. ``research_quick_brief`` — atalho raw-search (research_quick_search).
3. ``research_synthesis`` — re-format por audience/length (write_report).
4. ``research_health_diagnose`` — triagem de erros (/health + /metrics).

Adicionados em v2.3.0: ``research_quick_brief``, ``research_synthesis``,
``research_health_diagnose``.
"""

from percival_research.app import mcp
from utils import (
    create_health_diagnose_prompt,
    create_quick_brief_prompt,
    create_research_prompt,
    create_synthesis_prompt,
)


@mcp.prompt("research_query")
def research_query(
    topic: str,
    goal: str = "Sintetize os melhores resultados",
    report_format: str = "research_report",
) -> str:
    """Plan a deep research session (workflow completo).

    Use este prompt quando o agente precisa de um **report sintetizado
    multi-source** (30–120s, com LLM). Para snippets crus, prefira
    ``research_quick_brief``. Para troubleshoot de erro, prefira
    ``research_health_diagnose``.

    Args:
        topic: Tópico da pesquisa (sanitizado via ``sanitize_topic``).
        goal: Objetivo livre do agente, em linguagem natural. Quando
            vazio ou ``None``, cai no default.
        report_format: Formato do report final (research_report,
            summary, etc.).

    Returns:
        Texto do prompt renderizado; inclui cabeçalho "Please research..."
        e as instruções operacionais para usar ``research_deep``,
        ``research_get_*`` e ``research_write_report`` via MCP. Se algum
        argumento for inválido, retorna string ``[VALIDATION ERROR: ...]``.
    """
    try:
        return create_research_prompt(topic, goal, report_format)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"


@mcp.prompt("research_quick_brief")
def research_quick_brief(topic: str) -> str:
    """Quick raw-search for a topic — no synthesis, no LLM cost (v2.3.0+).

    Use este prompt quando o agente precisa de **5–10 snippets crus**
    sobre um tópico em **3–10s** sem acionar a pipeline completa.

    Diferente de ``research_query``, este prompt:
    - Não usa LLM (só busca no retriever configurado).
    - Não retorna ``research_id`` — não há follow-up com
      ``write_report``.

    Args:
        topic: Tópico para brief (raw — sanitizado via ``sanitize_topic``).

    Returns:
        Markdown-formatted prompt com DO/DON'T blocks e reminder de
        segurança. Se ``topic`` for inválido, retorna
        ``[VALIDATION ERROR: ...]``.
    """
    try:
        return create_quick_brief_prompt(topic)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"


@mcp.prompt("research_synthesis")
def research_synthesis(
    research_id: str,
    audience: str = "general",
    length: str = "medium",
) -> str:
    """Re-synthesize an existing research for a different audience (v2.3.0+).

    Use este prompt quando o agente tem um ``research_id`` (de uma
    chamada anterior a ``research_deep``) e quer um **output re-formatado**
    — ex.: TL;DR para executivo, paper-style para acadêmico.

    Args:
        research_id: UUID de uma sessão de pesquisa válida (validado
            via ``validate_research_id``).
        audience: ``general`` (default) | ``executive`` | ``technical``
            | ``academic``. Allowlist validada.
        length: ``tl_dr`` | ``short`` | ``medium`` (default) | ``long``.
            Allowlist validada.

    Returns:
        Prompt com spec audience×length + reminder para o agente usar
        ``write_report(research_id, custom_prompt=...)``. Erros de
        validação retornam ``[VALIDATION ERROR: ...]``.
    """
    try:
        return create_synthesis_prompt(research_id, audience, length)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"


@mcp.prompt("research_health_diagnose")
def research_health_diagnose(symptoms: str) -> str:
    """Triage de erros do MCP server (v2.3.0+).

    Use este prompt quando o agente recebe um ``Error: ...`` ou
    ``[SECURITY WARNING: ...]`` de qualquer tool do MCP. O prompt
    conduz o agente a:
    1. Inspecionar ``/health`` e ``/metrics``.
    2. Aplicar uma decision tree (retry / rephrase / escalate / bug).
    3. Reportar com evidência concreta.

    Args:
        symptoms: Texto livre com o erro observado (raw). Sanitizado
            via ``sanitize_prompt`` (limite definido por MAX_PROMPT_LEN
            em ``utils``). Strings vazias ou somente whitespace viram
            ``"(no symptoms provided)"``.

    Returns:
        Prompt com instrução passo-a-passo (5 passos numerados).
    """
    try:
        return create_health_diagnose_prompt(symptoms)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}. Please review the parameters.]"