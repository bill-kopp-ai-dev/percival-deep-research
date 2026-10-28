"""Resource: research://{topic}."""

import asyncio
import time

import percival_research.app as _app
from percival_research.app import (
    mcp,
)
from percival_research.research_worker_client import run_research_worker
from utils import (
    format_context_with_sources,
    handle_exception,
    new_correlation_id,
    sanitize_topic,
    wrap_untrusted_content,
)


async def _run_research_and_cache(query: str, cid: str) -> str:
    """Helper compartilhado: roda a pesquisa (com timeout rígido) e cacheia.

    Returns:
        Conteúdo formatado com warning header.

    Robustez (audits acumulada):
      - Respeita o mesmo `research_timeout_s` da tool `deep_research`,
        para garantir paridade de comportamento entre os dois endpoints.
      - A pesquisa roda em um processo isolado (`research_worker_client`),
        de modo que o limite de duração seja efetivo mesmo quando o
        upstream absorve o cancelamento.
      - Trata `source_urls = None` (algumas versões do gpt-researcher).
      - Audit rodada 3 BUG-3R-3: chama `metrics.record_latency` /
        `record_error` / `record_timeout` para que o endpoint
        `research://{topic}` seja visível em `/metrics`. Antes era
        invisível para observabilidade.
    """
    timeout_s = _app._settings.research_timeout_s

    start = time.monotonic()
    try:
        try:
            context, sources, source_urls = await run_research_worker(query, timeout_s)
        except asyncio.TimeoutError:
            _app.metrics.record_timeout("research_resource")
            # Round 6 fix (bug-hunt): timeouts não estavam alimentando o
            # deque de latências, enviesando p50_latency_ms em direção
            # aos sucessos rápidos. Agora todos os caminhos de saída
            # chamam record_latency.
            elapsed_ms = (time.monotonic() - start) * 1000
            _app.metrics.record_latency("research_resource", elapsed_ms)
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

    safe_formatted = wrap_untrusted_content(format_context_with_sources(query, context, sources))
    _app.registry.store(query, context, sources, source_urls, safe_formatted)
    elapsed_ms = (time.monotonic() - start) * 1000
    _app.metrics.record_latency("research_resource", elapsed_ms)
    return safe_formatted


@mcp.resource("research://{topic}")
async def research_resource(topic: str) -> str:
    """Web research cache for a topic, percent-encoding tolerant.

    URI: ``research://{topic}`` (use percent-encoding for whitespace or
    non-ASCII). Example — topic ``São Paulo``::

        research://S%C3%A3o%20Paulo

    The FastMCP client percent-encodes automatically when callers invoke
    via ``client.read_resource(uri)``. Operators building URIs by hand
    must percent-encode any whitespace, slashes, or non-ASCII chars to
    avoid Pydantic URL-domain validation errors.

    Returns the synthesized research context for the topic, looking up
    the local cache first and falling back to a fresh multi-source
    research run. Output is wrapped in a security banner.
    """
    from urllib.parse import unquote

    cid = new_correlation_id()

    # B1 fix: decode percent-encoded chars (e.g. ``%20`` → space) BEFORE
    # validation. Some agents and CLI tools already encode the URI; others
    # pass raw topic strings. In either case, decode first so sanitize_topic
    # handles the canonical form.
    try:
        topic_decoded = unquote(topic, errors="replace")
    except (TypeError, ValueError):
        topic_decoded = topic

    try:
        topic = sanitize_topic(topic_decoded)
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

    try:
        return await _run_research_and_cache(topic, cid)
    except Exception as e:
        _app.metrics.record_error("research_resource")
        return handle_exception(e, f"Research resource ({topic!r})", cid)
