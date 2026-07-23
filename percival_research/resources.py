"""Resource: research://{topic}."""

import asyncio
import sys
import time
from contextlib import redirect_stdout

from gpt_researcher import GPTResearcher

import percival_research.app as _app
from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    mcp,
)
from utils import (
    format_context_with_sources,
    handle_exception,
    new_correlation_id,
    sanitize_topic,
    wrap_untrusted_content,
)


async def _run_research_and_cache(query: str, factory, cid: str) -> str:
    """Helper compartilhado: cria researcher, faz conduct_research (com timeout)
    e cacheia.

    Returns:
        Conteúdo formatado com warning header.

    Robustez (audits acumulada):
      - Respeita o mesmo `research_timeout_s` da tool `deep_research`,
        para garantir paridade de comportamento entre os dois endpoints.
      - Trata `source_urls = None` (algumas versões do gpt-researcher).
      - Audit rodada 3 BUG-3R-3: chama `metrics.record_latency` /
        `record_error` / `record_timeout` para que o endpoint
        `research://{topic}` seja visível em `/metrics`. Antes era
        invisível para observabilidade.
    """
    researcher = factory(query)
    timeout_s = _app._settings.research_timeout_s

    async def _do_research():
        with redirect_stdout(sys.stderr):
            await researcher.conduct_research()

    start = time.monotonic()
    try:
        try:
            await asyncio.wait_for(_do_research(), timeout=timeout_s)
        except asyncio.TimeoutError:
            _app.metrics.record_timeout("research_resource")
            sys.stderr.write(
                f"research://{query!r} timed out after {timeout_s}s\n"
            )
            return (
                f"[RESOURCE TIMEOUT] Research exceeded the {timeout_s}s "
                f"internal limit (correlation_id={cid})."
            )
    except Exception as e:
        # Erro genérico (não-timeout) — não tenta cachear; apenas loga métrica.
        _app.metrics.record_error("research_resource")
        elapsed_ms = (time.monotonic() - start) * 1000
        _app.metrics.record_latency("research_resource", elapsed_ms)
        return handle_exception(e, f"Research resource ({query!r})", cid)

    try:
        # `get_research_sources` pode retornar None; também defensivamente
        # tratamos `context` como string (audit rodada 3).
        context = researcher.get_research_context()
        sources = researcher.get_research_sources() or []
        source_urls = researcher.get_source_urls() or []
    except Exception as e:
        _app.metrics.record_error("research_resource")
        elapsed_ms = (time.monotonic() - start) * 1000
        _app.metrics.record_latency("research_resource", elapsed_ms)
        return handle_exception(e, f"Research resource ({query!r})", cid)

    safe_formatted = wrap_untrusted_content(
        format_context_with_sources(query, context, sources)
    )
    _app.registry.store(query, context, sources, source_urls, safe_formatted)
    elapsed_ms = (time.monotonic() - start) * 1000
    _app.metrics.record_latency("research_resource", elapsed_ms)
    return safe_formatted


@mcp.resource("research://{topic}")
async def research_resource(topic: str) -> str:
    """..."""
    cid = new_correlation_id()
    try:
        topic = sanitize_topic(topic)
    except ValueError as e:
        return f"[VALIDATION ERROR: {e}]"

    # Cache check + eventual fallback para nova pesquisa, com cleanup
    # de erro entre as duas chamadas (impede TOCTOU entre has_topic e
    # get_cached onde uma evicção FIFO poderia dar `False` em has_topic
    # mas a entrada ainda existir).
    try:
        cached = _app.registry.get_cached(topic)
    except Exception:
        cached = None

    if cached is not None:
        return cached

    def factory(q):
        return GPTResearcher(
            query=q,
            agent=UNIVERSAL_AGENT_NAME,
            role=_app._get_universal_agent_role(),  # dinâmico (audit rodada 2)
            verbose=False,
        )

    try:
        return await _run_research_and_cache(topic, factory, cid)
    except Exception as e:
        _app.metrics.record_error("research_resource")
        return handle_exception(e, f"Research resource ({topic!r})", cid)