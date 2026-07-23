"""Fixtures compartilhadas para testes do servidor."""

import os
import socket
import uuid as _uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────
# B4 fix (rodada 3): autouse fixture que pula testes de integração
# (`@pytest.mark.integration`) quando não há server rodando em
# localhost:PORT (default 8000). Sem esse skip, todo CI limpo sem
# server reporta `1 failed` por sessão.
# ─────────────────────────────────────────────────────────────────

# Configurável via env var para ambientes com porta custom:
_PORT_FOR_INTEGRATION = int(os.getenv("PERCIVAL_TEST_PORT", 8000))
_HOST_FOR_INTEGRATION = os.getenv("PERCIVAL_TEST_HOST", "localhost")


def _probe_server(host: str, port: int, timeout: float = 0.5) -> bool:
    """Retorna True se `host:port` aceita conexões TCP em até `timeout`s.

    Não verifica HTTP — só faz connect. Se `httpx.ConnectError` existir
    porque o server não responde HTTP, o teste de integração vai ser
    explícito (mais útil do que um skip silencioso)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except (OSError, ConnectionRefusedError, socket.timeout):
        return False
    finally:
        sock.close()


@pytest.fixture(autouse=True)
def _skip_integration_tests_without_server(request):
    """Skip tests marcados `@pytest.mark.integration` se não houver server.

    Também serve para os testes em `test_mcp_server.py::test_*` que
    usam `http_client` (uma fixture integration-like) quando rodados
    sem servidor — eles dependem dela, então `http_client` está
    protegido de outra forma via lazy import.
    """
    mark = request.node.get_closest_marker("integration")
    if mark is None:
        return  # Não é integration — não skip.
    if _probe_server(_HOST_FOR_INTEGRATION, _PORT_FOR_INTEGRATION):
        return  # Server up — segue.
    pytest.skip(
        f"Integration test requires server on "
        f"{_HOST_FOR_INTEGRATION}:{_PORT_FOR_INTEGRATION}. "
        f"Start with `uv run percival-deep-research` (transport=sse) "
        f"or set PERCIVAL_TEST_HOST/PERCIVAL_TEST_PORT if remote."
    )


@pytest.fixture
def isolated_env(monkeypatch):
    """Limpa variáveis de ambiente relevantes para cada teste."""
    for k in [
        "PERCIVAL_MAX_RESEARCHERS",
        "PERCIVAL_RESEARCHER_TTL_S",
        "PERCIVAL_MAX_CACHED_TOPICS",
        "PERCIVAL_RESEARCH_TIMEOUT_S",
        "PERCIVAL_MAX_CONCURRENT_RESEARCH",
        "PERCIVAL_DEBUG_LOG_QUERIES",
        "MCP_TRANSPORT",
        "MCP_HOST",
        "PORT",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "FAST_LLM",
        "SMART_LLM",
        "STRATEGIC_LLM",
    ]:
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def mock_researcher():
    """Mock de GPTResearcher com métodos configuráveis."""
    r = MagicMock()
    r.conduct_research = AsyncMock()
    r.write_report = AsyncMock(return_value="# Mock Report\n\nConteúdo do relatório.")
    r.quick_search = AsyncMock(return_value=[
        "Snippet 1", "Snippet 2", "Snippet 3",
    ])
    r.get_research_context = MagicMock(return_value="Contexto sintetizado.")
    r.get_research_sources = MagicMock(return_value=[
        {"title": "Doc 1", "url": "https://a.com", "content": "abc"},
        {"title": "Doc 2", "url": "https://b.com", "content": "defg"},
    ])
    r.get_source_urls = MagicMock(return_value=["https://a.com", "https://b.com"])
    return r


@pytest.fixture
def registry():
    """Registry limpo para cada teste."""
    from utils import ResearchRegistry
    return ResearchRegistry()


@pytest.fixture
def mock_gpt_researcher(mock_researcher, monkeypatch):
    """Substitui GPTResearcher por mock em todos os pontos onde é usado."""
    # Fase 6: deep_research e quick_search estão em percival_research.tools.*
    # Resources também usa (resources.py).
    # write_report NÃO usa GPTResearcher (usa registry.get_researcher).
    # O mock é opcional — usado por testes que fazem deep_research + write_report.
    for path in [
        "percival_research.tools.deep_research.GPTResearcher",
        "percival_research.tools.quick_search.GPTResearcher",
        "percival_research.resources.GPTResearcher",
    ]:
        try:
            monkeypatch.setattr(path, lambda **kwargs: mock_researcher)
        except AttributeError:
            # Se o módulo não importar GPTResearcher (ex: write_report),
            # não falha.
            pass
    return mock_researcher


@pytest.fixture
def clean_app_state(monkeypatch):
    """Zera registry + metrics + limiter globais para isolar testes.

    Audit rodada 2: testes herdados anteriormente compartilhavam o
    `registry` e `research_limiter` globais (de `percival_research.app`),
    e ao rodar em sequência alguns testes saturavam o rate-limiter (3
    slots), fazendo testes posteriores retornarem
    "Server is busy (concurrent research limit reached)". Esta fixture
    garante isolamento via monkeypatch.
    """
    from utils import ResearchRegistry
    fresh_registry = ResearchRegistry()
    fresh_metrics = None

    try:
        from percival_research import app as _app
        from utils import Metrics, RateLimiter
        fresh_metrics = Metrics()
        fresh_limiter = RateLimiter(max_concurrent=100)  # alto em testes
        monkeypatch.setattr(_app, "registry", fresh_registry)
        monkeypatch.setattr(_app, "metrics", fresh_metrics)
        monkeypatch.setattr(_app, "research_limiter", fresh_limiter)
    except ImportError:
        pass

    return {
        "registry": fresh_registry,
        "metrics": fresh_metrics,
    }