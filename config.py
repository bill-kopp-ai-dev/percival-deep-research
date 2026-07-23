"""
Configurações centralizadas do servidor.

Todas as constantes de runtime são lidas de variáveis de ambiente aqui.
Defaults são definidos explicitamente. Sem tocar este arquivo ou
.env.example, o operador controla o comportamento do servidor.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int | None = None) -> int:
    """Lê inteiro com validação de faixa + warn explícito em entrada inválida.

    Comportamento:
        - Var não-setada → default.
        - Var inválida (não-numérica) → warn + default.
        - Var fora de [min_value, max_value] → warn + default.

    Por que fallback (em vez de raise) pra typos de operador: o servidor
    subiu em produção ainda é melhor do que ele não subir — mas o log
    garante que a misconfig seja visível no observability stack.
    """
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


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").lower() == "true"


def _env_str_choice(name: str, default: str, choices: set[str]) -> str:
    """Lê string que deve estar no conjunto `choices` (case-insensitive)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    val = raw.lower() if name.endswith(("LOG_LEVEL", "MCP_TRANSPORT")) else raw
    # Normalização específica por var — manter simple:
    if name in {"LOG_LEVEL"}:
        val = raw.upper()
    elif name in {"MCP_TRANSPORT"}:
        val = raw.lower()
    else:
        val = raw
    if val not in choices:
        print(
            f"WARN: env {name}={raw!r} not in {sorted(choices)}; using default={default}",
            file=sys.stderr,
        )
        return default
    return val


@dataclass(frozen=True)
class Settings:
    """Snapshot imutável de configuração no startup."""

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

    # ── LLM bridge ──
    llm_provider_aliases: tuple
    minimax_model_alias: str
    minimax_alias_pattern: str


def load_settings() -> Settings:
    """Carrega settings do ambiente, com defaults sensatos.

    Para aliases de provider: `PERCIVAL_LLM_PROVIDER_ALIASES` é uma
    lista separada por vírgulas (ex.: "venice:,minimax:,openrouter:,
    deepseek:"). Permite ao operador adicionar novos aliases sem
    editar o código.
    """
    # Lê tupla de aliases separados por vírgula
    raw_aliases = os.getenv(
        "PERCIVAL_LLM_PROVIDER_ALIASES",
        "venice:,minimax:,openrouter:",
    )
    aliases = tuple(
        a.strip() for a in raw_aliases.split(",") if a.strip()
    )
    # Garante termina com ":" (para fazer prefix-match)
    aliases = tuple(a if a.endswith(":") else f"{a}:" for a in aliases)

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

        # LLM bridge
        llm_provider_aliases=aliases,
        minimax_model_alias=_env_str("MINIMAX_MODEL_ALIAS", "MiniMax-M2.7"),
        minimax_alias_pattern=(
            _env_str("MINIMAX_ALIAS_PATTERN", "minimax-m27")
            or "minimax-m27"  # nunca vazio (corromperia re.sub)
        ),
    )