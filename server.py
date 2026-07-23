"""
Percival Deep Research MCP Server — entrypoint.

Module structure:
- config.py: Settings (frozen dataclass, env-driven)
- llm_bridge.py: Normalize venice:/minimax:/openrouter: → openai:
- utils.py: Security, registry, formatters, Metrics, RateLimiter
- percival_research/: app, tools, resources, prompts, health, metrics, patches
"""

import os

from fastmcp import FastMCP
from loguru import logger

from percival_research import __version__
from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    UNIVERSAL_AGENT_ROLE,
    _settings,
    mcp,
    metrics,
    registry,
    research_limiter,
)
from percival_research.health import _check_inference_configured, _check_retriever_configured
from percival_research.patches import apply_compressor_patch

# Side-effects: registrar tools, resource e prompt via decorators @mcp.*.
import percival_research.tools as _tools  # noqa: F401  (registra tools via decorators)
from percival_research.tools.deep_research import deep_research  # noqa: F401
from percival_research.tools.quick_search import quick_search  # noqa: F401
from percival_research.tools.write_report import write_report  # noqa: F401
from percival_research.tools.get_research_context import get_research_context  # noqa: F401
from percival_research.tools.get_research_sources import get_research_sources  # noqa: F401
from percival_research import resources as _resources  # noqa: F401
from percival_research import prompts as _prompts  # noqa: F401
from percival_research.health import health_check  # noqa: F401  (registra /health)
from percival_research.metrics import metrics_endpoint  # noqa: F401  (registra /metrics)

# Aplicar monkey-patch do compressor (com guarda) cedo.
_PATCH_OK = apply_compressor_patch()

# Re-exports para testes e callers que importam de `server`.
from utils import (  # noqa: E402, F401
    Metrics,
    RateLimiter,
    format_sources_lines,
    new_correlation_id,
    rate_limited,
    validate_research_id,
)
# Alias histórico (rodada 3): `_validate_research_id` foi usado por 21 testes.
# Mantido para compat até os testes serem migrados para `validate_research_id`.
_validate_research_id = validate_research_id

# Re-export do resource / prompt para testes e compat.
research_resource = _resources.research_resource
research_query = _prompts.research_query
# v2.3.0 — 3 prompts adicionais
research_quick_brief = _prompts.research_quick_brief
research_synthesis = _prompts.research_synthesis
research_health_diagnose = _prompts.research_health_diagnose


def run_server() -> None:
    """Starts the MCP server using the transport configured via env."""
    settings = _settings

    # Aplica `log_level` configurado (audit-11 — antes era dead code).
    # Audit rodada 3 BUG-server: wrappa o bloco inteiro em try/finally
    # para restaurar os sinks default do logger (caso mcp.run ou check
    # inicial disparem exit/return que deixam sinks mutados para
    # módulos vizinhos no mesmo processo).
    import sys as _sys
    try:
        logger.remove()  # remove o default sink
        logger.add(_sys.stderr, level=settings.log_level)
    except Exception:
        pass

    # Bloco Try/finally para restaurar logger.configure default após
    # conclusão do servidor (incluindo early-return).
    try:
        # v2.2: checa credenciais usando o canônico `INFERENCE_*` com
        # fallback OpenAI*. Mensagem atualizada para refletir o nome novo.
        if not _check_inference_configured():
            logger.error(
                "INFERENCE_API_KEY (or INFERENCE_BASE_URL for a custom gateway) "
                "not found. Set it in your .env file, or use the legacy "
                "OPENAI_API_KEY / OPENAI_BASE_URL."
            )
            return

        transport = settings.mcp_transport
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            transport = "sse"
            logger.info("Docker environment detected — switching to SSE transport.")

        # v2.2: loga o provider auto-detectado e o LLM em uso para
        # facilitar o debug operacional (operador vê na log ao subir).
        if settings.inference_provider_alias:
            logger.info(
                f"Inference provider: {settings.inference_provider_alias} "
                f"(auto-detected from INFERENCE_BASE_URL)"
            )
        logger.info(f"Inference LLM: {settings.inference_llm}")
        logger.info(f"Default retriever: {settings.default_retriever}")

        logger.info(
            f"Starting GPT Researcher MCP Server v{__version__} with transport: {transport}"
        )

        if transport == "stdio":
            logger.info("STDIO transport (compatible with Nanobot and Claude Desktop)")
            mcp.run(transport="stdio")
        elif transport == "sse":
            logger.info(
                f"SSE mode — binding to {settings.mcp_host}:{settings.mcp_port}"
            )
            mcp.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
        elif transport == "streamable-http":
            logger.info(
                f"Streamable-HTTP mode — binding to "
                f"{settings.mcp_host}:{settings.mcp_port}"
            )
            mcp.run(
                transport="streamable-http",
                host=settings.mcp_host,
                port=settings.mcp_port,
            )
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
    finally:
        # Audit rodada 3 BUG-server: restaura o sink default configurado
        # por `utils.configure` no import-time. Garante que módulos
        # vizinhos no processo (ex.: pytest) tenham logger utilizável.
        try:
            logger.remove()
        except Exception:
            pass
        # Re-aplica o default sink do loguru (stderr com level INFO).
        logger.add(_sys.stderr, level="INFO")


if __name__ == "__main__":
    run_server()