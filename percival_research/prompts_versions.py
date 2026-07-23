"""
Versionamento de prompts (Fase 7).

Permite A/B testing e rollback via env `PERCIVAL_PROMPT_VERSION`.
"""

import sys

V1_RESEARCH_AGENT_ROLE = (
    "You are an experienced AI research assistant. Your primary goal is to "
    "critically analyze information, synthesize findings, cross-reference sources, "
    "and produce highly accurate, objective, and well-structured reports on the "
    "given topic."
)

V2_RESEARCH_AGENT_ROLE = V1_RESEARCH_AGENT_ROLE + (
    " When uncertain, prefer acknowledging gaps over fabricating details."
)

_KNOWN_VERSIONS = {"v1", "v2"}


def get_research_agent_role() -> str:
    """Retorna o role do agent de pesquisa baseado em `PERCIVAL_PROMPT_VERSION`.

    Audit rodada 2 BUG-cleanups: typos no env (ex.: `v3`, `V1` com case)
    agora logam WARN em stderr para que o operador perceba.
    """
    import os
    raw = os.getenv("PERCIVAL_PROMPT_VERSION", "v1")
    if raw == "v2":
        return V2_RESEARCH_AGENT_ROLE
    if raw == "v1":
        return V1_RESEARCH_AGENT_ROLE
    # Valor desconhecido → fallback com WARN para debug operacional.
    print(
        f"WARN: PERCIVAL_PROMPT_VERSION={raw!r} não reconhecido; "
        f"esperado um de {sorted(_KNOWN_VERSIONS)}; usando v1.",
        file=sys.stderr,
    )
    return V1_RESEARCH_AGENT_ROLE