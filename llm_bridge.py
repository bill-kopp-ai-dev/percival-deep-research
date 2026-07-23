"""
LLM bridge (v2.2.0) — normaliza o env para o formato aceito pelo gpt-researcher.

Mudanças de v2.2:
- O operador passa UM `INFERENCE_LLM` no ambiente.
- Esta camada preenche FAST_LLM / SMART_LLM / STRATEGIC_LLM /
  EMBEDDING_LLM com esse valor (a menos que o operador tenha
  customizado explicitamente).
- Aliases de provider (venice:, minimax:, openrouter:) são reconhecidos
  automaticamente a partir de `INFERENCE_BASE_URL` (auto-detect).

gpt-researcher aceita apenas "openai:" (que mapeia para ChatOpenAI).
Tudo que não começa com "openai:" é traduzido para o prefixo nativo
"openai:<resto>", e correções case-sensitive são aplicadas para MiniMax.

Compatibilidade:
- OPENAI_API_KEY / OPENAI_BASE_URL são lidas via config (fallback).
- OPENAI_API_BASE é reconhecido em `run_server` apenas para descobrir
  o LLM string.
"""

from __future__ import annotations

import os
import re

from config import Settings


# ---------------------------------------------------------------------------
# Constantes de slot
# ---------------------------------------------------------------------------
# gpt-researcher consulta estas 4 vars para diferentes tarefas:
# - STRATEGIC_LLM: planning (mais capacidade)
# - FAST_LLM: summaries / extraction (mais barato)
# - SMART_LLM: research synthesis (intermediário)
# - EMBEDDING_LLM: embeddings (desativado pelo patch do compressor, mas
#                   setamos para garantir consistência)
_SLOT_VARS = ("STRATEGIC_LLM", "FAST_LLM", "SMART_LLM", "EMBEDDING_LLM")


def populate_inference_slots(settings: Settings) -> None:
    """Se nenhuma das 4 slot-vars foi setada explicitamente pelo operador,
    preenche com `INFERENCE_LLM` (fonte canônica única).

    Esta é a função que efetiva o modelo "um LLM só" para o servidor.
    Chamada idempotente — apenas popula vars que ainda estão unset.
    """
    if not settings.inference_llm:
        # Sem INFERENCE_LLM, não inventar valor — só preenche se já tiver.
        return

    for var in _SLOT_VARS:
        if not os.getenv(var):
            os.environ[var] = settings.inference_llm


def apply_env_mappings(settings: Settings) -> None:
    """Aplica mapeamentos no env para que o gpt-researcher enxergue
    config consistente. Chamada no startup; idempotente.

    Ordem de operações:
      1. `populate_inference_slots` — preenche slots vazios com INFERENCE_LLM.
      2. Traduzir aliases de provider em todos os slots setados.
      3. Aplicar correção de alias MiniMax (case-sensitive).
    """
    populate_inference_slots(settings)
    _translate_all_slots(settings)


def _translate_all_slots(settings: Settings) -> None:
    """Para cada slot setado no env (FAST/SMART/STRATEGIC/EMBEDDING/INFERENCE),
    aplica `_translate_provider` e `_apply_minimax_alias`.
    Idempotente — só reescreve se o valor mudar."""
    seen: set[str] = set()
    for var in (*_SLOT_VARS, "INFERENCE_LLM"):
        if var in seen:
            continue
        val = os.getenv(var)
        if not val:
            continue
        original = val
        val = _translate_provider(val, settings)
        val = _apply_minimax_alias(val, settings)
        if val != original:
            os.environ[var] = val
            seen.add(var)


def normalize_llm_env(settings: Settings) -> None:
    """Compat wrapper — chamada legada por server.py.

    Internamente delega para `apply_env_mappings` (mesma semântica).
    Mantida para preservar imports antigos (tests/__init__ etc.).
    """
    apply_env_mappings(settings)


def _translate_provider(val: str, settings: Settings) -> str:
    """Se `val` começa com algum alias registrado (ex.: ``venice:``), traduz
    para ``openai:<resto>`` (porque gpt-researcher só entende `openai:`).
    """
    # Ordem: percorre aliases (que já incluem o auto-detectado no início).
    for prefix in settings.llm_provider_aliases:
        if val.startswith(prefix):
            rest = val[len(prefix):]
            return f"openai:{rest}"
    return val


def _apply_minimax_alias(val: str, settings: Settings) -> str:
    """Substitui o pattern ``minimax-m27`` pelo alias canônico
    ``MiniMax-M2.7`` se encontrado. Necessário porque o SDK do provider
    é case-sensitive neste nome."""
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