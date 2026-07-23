"""Aplicação FastMCP e globais do servidor."""

from fastmcp import FastMCP

from config import load_settings
from llm_bridge import normalize_llm_env
from utils import Metrics, RateLimiter, ResearchRegistry

# Single source of truth (audit rodada 2): load settings once and use it.
_settings = load_settings()
normalize_llm_env(_settings)

mcp = FastMCP(name="percival_deep_research")
registry = ResearchRegistry(settings=_settings)

# Audit rodada 2 BUG-12: limiter lazy (cria semáforo no event-loop atual,
# em vez do import-time) — evita erro "Semaphore bound to a different
# event loop" em testes (cada teste cria seu próprio loop).
research_limiter = RateLimiter(max_concurrent=_settings.max_concurrent_research)

metrics = Metrics()

UNIVERSAL_AGENT_NAME = "💻 Deep Research Agent"


def _get_universal_agent_role() -> str:
    """Audit rodada 2 BUG-stale-closure: função getter para que tools
    sempre leiam o role do estado atual (após `importlib.reload`) em vez
    de capturar valor fixo no import-time.
    """
    from percival_research.prompts_versions import get_research_agent_role
    return get_research_agent_role()


# Mantido para compat com callers que faziam `from app import UNIVERSAL_AGENT_ROLE`.
# NOTA: este valor é capturado uma vez no import. Use `_get_universal_agent_role()`
# em runtime se quiser ler o estado atual.
UNIVERSAL_AGENT_ROLE = _get_universal_agent_role()

__all__ = [
    "mcp",
    "registry",
    "research_limiter",
    "metrics",
    "UNIVERSAL_AGENT_NAME",
    "UNIVERSAL_AGENT_ROLE",
    "_settings",
]