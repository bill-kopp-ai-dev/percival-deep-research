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

from loguru import logger

from config import Settings
from utils import PLACEHOLDER_OPENERS


# ---------------------------------------------------------------------------
# Constantes de slot
# ---------------------------------------------------------------------------
# gpt-researcher consulta estas 4 vars para diferentes tarefas:
# - STRATEGIC_LLM: planning (mais capacidade)
# - FAST_LLM: summaries / extraction (mais barato)
# - SMART_LLM: research synthesis (intermediário)
# - EMBEDDING_LLM: embeddings (desativado pelo patch do compressor; mas
#                   se setado, gpt-researcher o instancia no `__init__`
#                   ANTES do pipeline principal — por isso precisa ser
#                   um modelo de embedding válido, e NÃO o mesmo chat-model).
_CHAT_SLOT_VARS = ("STRATEGIC_LLM", "FAST_LLM", "SMART_LLM")
_EMBEDDING_SLOT_VARS = ("EMBEDDING_LLM",)
_SLOT_VARS = (*_CHAT_SLOT_VARS, *_EMBEDDING_SLOT_VARS)

# Default sensato para embeddings. Documentado em CHANGELOG v2.2.1.
# Se o provider tem um equivalente, o operador pode sobrescrever
# via env `EMBEDDING_LLM`. Se não — gpt-researcher falha limpo
# (em vez de gerar embeddings lixo a partir de um chat-model).
_DEFAULT_OPENAI_EMBEDDING = "openai:text-embedding-3-small"


def populate_inference_slots(settings: Settings) -> None:
    """Se nenhuma das slot-vars foi setada explicitamente pelo operador,
    preenche com `INFERENCE_LLM` (fonte canônica única) para os 3 slots
    de chat. Embeddings recebe default sensato apenas quando o provider
    tem modelos de embedding compatíveis.

    Bug audit (B3/B5 fix) — esta função também propaga `INFERENCE_*`
    para o namespace legacy `OPENAI_*` que `gpt-researcher/memory/embeddings.py`
    continua lendo em seu `OpenAIEmbeddings.__init__`. Sem esse
    bridging, embeddings sempre cai no endpoint OpenAI nativo com
    a chave configurada, quebrando qualquer deployment em gateway
    custom (Venice, MiniMax, OpenRouter, local LM Studio etc.).

    Esta é a função que efetiva o modelo "um LLM só" para o servidor.
    Chamada idempotente — apenas popula vars que ainda estão unset.

    Note (review-5): warn de INFERENCE_LLM mal-formado é emitido em
    `config.load_settings` (`_sanitize_inference_llm_or_warn`), não
    aqui — emite no import-time garante uma única mensagem e cobre
    cenários onde `populate_inference_slots` não é chamado.
    """
    if not settings.inference_llm:
        # Sem INFERENCE_LLM, não inventar valor — só preenche se já tiver.
        return

    # 1. Chat slots: copia INFERENCE_LLM para STRATEGIC/FAST/SMART_LLM
    #    se nenhuma delas estiver setada. EMBEDDING_LLM NÃO recebe este
    #    valor (B5: gpt-4o-mini não é embedding model).
    for var in _CHAT_SLOT_VARS:
        if not os.getenv(var):
            os.environ[var] = settings.inference_llm

    # 2. Embedding slot: default sensato apenas quando o provider é
    #    OpenAI-compatível com embedding conhecido. Caso contrário, deixar
    #    unset (gpt-researcher falha limpo, em vez de aceitar silenciosamente
    #    um modelo errado e gerar embeddings lixo).
    if not os.getenv("EMBEDDING_LLM"):
        is_openai_compatible = "openai:" in settings.inference_llm
        if is_openai_compatible:
            os.environ["EMBEDDING_LLM"] = _DEFAULT_OPENAI_EMBEDDING

    # 3. Bridge BUG-3 fix: `gpt-researcher/memory/embeddings.py:104` ainda
    #    lê `os.environ["OPENAI_API_KEY"]` e `os.environ["OPENAI_BASE_URL"]`
    #    direto, ignorando nossa configuração canônica `INFERENCE_*`.
    #    Propagamos para o namespace legacy para que o embedding client
    #    seja instanciado com o MESMO endpoint/key que o chat client.
    if settings.inference_api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.inference_api_key
    if settings.inference_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = settings.inference_base_url


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


# ─────────────────────────────────────────────────────────────────────
# S4 (roda 5) — Malformed INFERENCE_LLM detection
# ─────────────────────────────────────────────────────────────────────
#
# Review-5: este helper foi removido daqui em favor do único local em
# `config._sanitize_inference_llm_or_warn` (avisa no import-time e uma
# só vez). Mantemos um stub thin wrapping-the-config-helper para
# compat retroativa de testes diretos (`test_warn`); mas é
# anticipated que futuro NaNo ramote pode remover este wrapper também.
# ─────────────────────────────────────────────────────────────────────


def _warn_on_malformed_inference_llm(value: str) -> None:
    """Compat wrapper — delega ao único local real em
    `config._sanitize_inference_llm_or_warn`.

    Mantido para retro-compat com `test_audit_round5_placeholder.py::TestWarnOnMalformedInferenceLLM`
    que importa o nome diretamente. Review-5 prefere o local único
    para evitar warnings duplicados.
    """
    from config import _sanitize_inference_llm_or_warn

    _sanitize_inference_llm_or_warn(value)


# Re-export PLACEHOLDER_OPENERS via _LIKELY_PLACEHOLDERS para
# retro-compat (test_audit_round5_placeholder.py pode referenciar).
_LIKELY_PLACEHOLDERS = PLACEHOLDER_OPENERS