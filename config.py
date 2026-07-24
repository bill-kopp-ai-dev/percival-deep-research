"""
Configurações centralizadas do servidor (v2.2.0).

Renomeações para clareza operacional (release v2.2.0):
- `INFERENCE_API_KEY` substitui `OPENAI_API_KEY`
- `INFERENCE_BASE_URL` substitui `OPENAI_BASE_URL`
- `INFERENCE_LLM` substitui as quatro vars FAST/SMART/STRATEGIC/EMBEDDING_LLM
- `RETRIEVER` default muda de `brave` para `duckduckgo`

As vars antigas (OPENAI_*, FAST_LLM/SMART_LLM/STRATEGIC_LLM/EMBEDDING_LLM,
PERCIVAL_LLM_PROVIDER_ALIASES) ainda funcionam como **fallback**,
logando WARN para operadores que ainda dependem delas.
Elas serão removidas em v3.0.0.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

from loguru import logger


_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int | None = None) -> int:
    """Lê inteiro com validação de faixa + warn explícito em entrada inválida."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        val = int(raw)
    except ValueError:
        print(
            f"WARN: env {name}={raw!r} is not an integer; using default={default}",
            file=sys.stderr,
        )
        return default
    if val < min_value or (max_value is not None and val > max_value):
        max_str = max_value if max_value is not None else "inf"
        print(
            f"WARN: env {name}={val} out of range [{min_value}, {max_str}]; "
            f"using default={default}",
            file=sys.stderr,
        )
        return default
    return val


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_str_fallback(primary: str, fallback: str, default: str = "") -> str:
    """Lê var com fallback automático. Logging:

    - Se `primary` setada → usa o valor dela silenciosamente.
    - Se só `fallback` setada → usa o valor dela + loga WARN
      recomendando migrar para `primary`.
    - Se nenhuma setada → retorna default (string vazia).
    """
    val = os.getenv(primary)
    if val:
        return val
    legacy = os.getenv(fallback)
    if legacy:
        print(
            f"WARN: env {fallback}=... is deprecated; "
            f"please set {primary} instead (will be removed in v3.0.0).",
            file=sys.stderr,
        )
        return legacy
    return default


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").lower() == "true"


def _env_str_choice(name: str, default: str, choices: set[str]) -> str:
    """Lê string que deve estar no conjunto `choices` (case-insensitive)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    val = raw
    if name.endswith("LOG_LEVEL"):
        val = raw.upper()
    elif name.endswith("MCP_TRANSPORT"):
        val = raw.lower()
    if val not in choices:
        print(
            f"WARN: env {name}={raw!r} not in {sorted(choices)}; using default={default}",
            file=sys.stderr,
        )
        return default
    return val


# Provider auto-detection (Fase 1 — simplificação de config).
# URL → prefixo de alias. Sem regex frágil: match exato de host.
_PROVIDER_URL_PATTERNS = [
    ("minimax", re.compile(r"api\.minimax\.io")),
    ("minimax", re.compile(r"api\.(?:minimax|minimax-m27)\.com")),
    ("venice", re.compile(r"api\.venice\.ai")),
    ("openrouter", re.compile(r"openrouter\.ai")),
]


def _detect_provider_alias(base_url: str) -> str | None:
    """Inspeciona `INFERENCE_BASE_URL` e devolve o alias de provider.

    Retorna `None` se não reconhecer (assume `openai:` nativo).
    """
    if not base_url:
        return None
    base_url = base_url.lower()
    for alias, pat in _PROVIDER_URL_PATTERNS:
        if pat.search(base_url):
            return alias
    return None


@dataclass(frozen=True)
class Settings:
    """Snapshot imutável de configuração no startup.

    v2.2.0: novos campos de inferência unificada (`inference_*`).
    Campos legados (`llm_provider_aliases`, etc.) são mantidos como
    representação de compat mas o código novo usa `inference_*`.
    """

    # ── Registry / Cache ──
    max_researchers: int
    researcher_ttl_s: int
    max_cached_topics: int
    cache_topic_ttl_s: int

    # ── Runtime ──
    research_timeout_s: int
    max_concurrent_research: int

    # ── Logging ──
    log_level: str
    debug_log_queries: bool

    # ── Transport ──
    mcp_transport: str
    mcp_host: str
    mcp_port: int

    # ── Inference (v2.2 — canônico) ──
    inference_api_key: str         # INFERENCE_API_KEY (fallback OPENAI_API_KEY)
    inference_base_url: str        # INFERENCE_BASE_URL (fallback OPENAI_BASE_URL)
    inference_llm: str             # INFERENCE_LLM (default: openai:gpt-4o-mini)
    inference_provider_alias: str | None  # auto-detectado da base_url (None se não reconhecido)
    default_retriever: str         # RETRIEVER (default: duckduckgo)

    # ── LLM bridge (legacy — fallback) ──
    llm_provider_aliases: tuple    # PERCIVAL_LLM_PROVIDER_ALIASES (deprecated)
    minimax_model_alias: str
    minimax_alias_pattern: str


def load_settings() -> Settings:
    """Carrega settings do ambiente, com defaults sensatos (v2.2).

    Novidades:
      - `INFERENCE_API_KEY` / `INFERENCE_BASE_URL` (com fallback OpenAI*).
      - `INFERENCE_LLM` (model string única para todos os slots LLM).
      - `inference_provider_alias` é auto-detectado a partir do
        `INFERENCE_BASE_URL` (e.g.: https://api.venice.ai/api/v1 → "venice").
      - `default_retriever` default = "duckduckgo" (sem chave de API).
    """
    # Inference (canônico, com fallback)
    inference_api_key = _env_str_fallback("INFERENCE_API_KEY", "OPENAI_API_KEY")
    inference_base_url = _env_str_fallback("INFERENCE_BASE_URL", "OPENAI_BASE_URL")
    inference_llm = os.getenv("INFERENCE_LLM", "openai:gpt-4o-mini")
    # S6 fix (roda 5): emite WARN cedo se `INFERENCE_LLM` está em formato
    # não reconhecido pelo gpt-researcher (<provider>:<model>). Sem este
    # guard, o erro só aparece deep inside `parse_llm`.
    inference_llm = _sanitize_inference_llm_or_warn(inference_llm)
    inference_provider_alias = _detect_provider_alias(inference_base_url)

    # Provider aliases legacy (PERCIVAL_LLM_PROVIDER_ALIASES) — fallback
    # automático se INFERENCE_BASE_URL não fornecer. Para v2.2, ainda
    # mantemos o suporte mas emitimos WARN quando a var legacy está
    # setada sem provider_alias auto-detectado.
    raw_aliases = os.getenv(
        "PERCIVAL_LLM_PROVIDER_ALIASES",
        "venice:,minimax:,openrouter:",
    )
    aliases = tuple(
        a.strip() for a in raw_aliases.split(",") if a.strip()
    )
    aliases = tuple(a if a.endswith(":") else f"{a}:" for a in aliases)
    # Se o provider auto-detectado não estiver nos aliases, prepend.
    if (
        inference_provider_alias
        and f"{inference_provider_alias}:" not in aliases
    ):
        aliases = (f"{inference_provider_alias}:",) + aliases

    return Settings(
        # Registry / Cache
        max_researchers=_env_int("PERCIVAL_MAX_RESEARCHERS", 50, min_value=1),
        researcher_ttl_s=_env_int("PERCIVAL_RESEARCHER_TTL_S", 3_600, min_value=1),
        max_cached_topics=_env_int("PERCIVAL_MAX_CACHED_TOPICS", 100, min_value=1),
        cache_topic_ttl_s=_env_int("PERCIVAL_CACHE_TOPIC_TTL_S", 3_600, min_value=1),

        # Runtime
        research_timeout_s=_env_int("PERCIVAL_RESEARCH_TIMEOUT_S", 90, min_value=1),
        max_concurrent_research=_env_int(
            "PERCIVAL_MAX_CONCURRENT_RESEARCH", 3, min_value=1, max_value=256,
        ),

        # Logging
        log_level=_env_str_choice("LOG_LEVEL", "INFO", _VALID_LOG_LEVELS),
        debug_log_queries=_env_bool("PERCIVAL_DEBUG_LOG_QUERIES", False),

        # Transport
        mcp_transport=_env_str_choice("MCP_TRANSPORT", "stdio", _VALID_TRANSPORTS),
        mcp_host=_env_str("MCP_HOST", "127.0.0.1"),
        mcp_port=_env_int("PORT", 8000, min_value=1, max_value=65535),

        # Inference (v2.2 — canônico)
        inference_api_key=inference_api_key,
        inference_base_url=inference_base_url,
        inference_llm=inference_llm,
        inference_provider_alias=inference_provider_alias,
        default_retriever=_env_str("RETRIEVER", "duckduckgo"),

        # Legacy
        llm_provider_aliases=aliases,
        minimax_model_alias=_env_str("MINIMAX_MODEL_ALIAS", "MiniMax-M2.7"),
        minimax_alias_pattern=(
            _env_str("MINIMAX_ALIAS_PATTERN", "minimax-m27")
            or "minimax-m27"  # nunca vazio (corromperia re.sub)
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# S6 (roda 5) — INFERENCE_LLM sanity-check
# ─────────────────────────────────────────────────────────────────────


_PLACEHOLDER_SIGNALS = (
    "${",          # bash-style `${VAR}` ou `${VAR:-default}`
    "%(",          # python `(name)s`
    "{",           # qualquer `{...}` (f-string, named placeholder)
    "}",           # fecha de `{...}`
)


def _sanitize_inference_llm_or_warn(value: str) -> str:
    """Emite WARN se `INFERENCE_LLM` parece placeholder (não-interpolado)
    e retorna o valor intacto (não bloqueia o startup — apenas alerta).

    O bug reproduzido (ver `MCP_Docs/Issues/2026-07-23-...-inference-llm-
    placeholder.md`) mostrou que `.nanobot-test/.env:89` segura
    `INFERENCE_API_KEY=${MINIMAX_API_KEY}` (literal bash-style) e
    `.nanobot-test/config.json:776` segura
    `INFERENCE_LLM=${INFERENCE_LLM:-openai:gpt-4o-mini}` — o resultado
    chegou literal em `gpt_researcher.config.config.parse_llm()` que
    corta no primeiro `:` e gera a mensagem erma
    `Unsupported ${INFERENCE_LLM.`.

    Importante: NÃO substituímos o valor por default (mesmo sendo capaz)
    — o operador pode ter um bom motivo para usar provider não-OpenAI.
    Apenas avisamos e deixamos ele investigar.
    """
    if not value:
        return value

    # Caso 1: sem `:` — formato errado para gpt-researcher.
    if ":" not in value:
        logger.warning(
            f"[S6] INFERENCE_LLM={value!r} does NOT match format "
            f"'<provider>:<model>'. gpt-researcher will raise "
            f"'Unsupported...' on first call. Fix: set INFERENCE_LLM "
            f"to a literal value like 'openai:gpt-4o-mini'."
        )
        return value

    # Caso 2: placeholder cru `${...}` ou similar.
    if any(sig in value for sig in _PLACEHOLDER_SIGNALS):
        logger.warning(
            f"[S6] INFERENCE_LLM={value!r} looks like an UN-EXPANDED "
            f"template placeholder. Most likely cause: `.env` or "
            f"`config.json` referenced a placeholder (e.g. "
            f"`${{INFERENCE_LLM:-openai:gpt-4o-mini}}`) that the loader "
            f"couldn't interpolate. Replace it with a literal value."
        )

    return value