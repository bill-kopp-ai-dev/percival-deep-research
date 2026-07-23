"""
LLM bridge — normaliza nomes de provider para o formato aceito pelo GPT Researcher.

gpt-researcher aceita apenas "openai:" (que mapeia para ChatOpenAI). Esta camada
traduz "venice:", "minimax:", "openrouter:" para "openai:<resto>", e aplica
correções case-sensitive para MiniMax.
"""

from __future__ import annotations

import os
import re

from config import Settings


def normalize_llm_env(settings: Settings) -> None:
    """Lê FAST_LLM / SMART_LLM / STRATEGIC_LLM / EMBEDDING_LLM e aplica traduções.

    Idempotente — chamou uma vez, chamar de novo não re-traduz.

    Note sobre `EMBEDDING_LLM`: gpt-researcher também consulta essa var para
    embeddings. Como nosso patch do compressor (_bypass) desativa embeddings,
    esta var normalmente não é usada — mas se um operador setar
    `EMBEDDING_LLM=venice:foo` (ou outro provider que não suporta
    embedding-OAI), o patch não pega, e o gpt_researcher pode falhar.
    Traduzimos proativamente.
    """
    already_translated: set[str] = set()
    for var in (
        "FAST_LLM",
        "SMART_LLM",
        "STRATEGIC_LLM",
        "EMBEDDING_LLM",
    ):
        val = os.getenv(var)
        if not val:
            continue
        original = val
        val = _translate_provider(val, settings)
        val = _apply_minimax_alias(val, settings)
        if val != original and var not in already_translated:
            os.environ[var] = val
            already_translated.add(var)


def _translate_provider(val: str, settings: Settings) -> str:
    for prefix in settings.llm_provider_aliases:
        if val.startswith(prefix):
            rest = val[len(prefix):]
            return f"openai:{rest}"
    return val


def _apply_minimax_alias(val: str, settings: Settings) -> str:
    # Guard contra pattern vazio (corromperia re.sub — "MiniMax-M2.7gpt-4o").
    pattern = settings.minimax_alias_pattern
    if not pattern:
        return val
    if pattern.lower() in val.lower():
        return re.sub(
            re.escape(pattern),
            settings.minimax_model_alias,
            val,
            flags=re.IGNORECASE,
        )
    return val