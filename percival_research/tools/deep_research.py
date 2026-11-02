"""Tool: deep_research — pesquisa profunda multi-fonte."""

import asyncio
import time
import uuid

from gpt_researcher import GPTResearcher
from loguru import logger
from pydantic import StrictBool

import percival_research.app as _app
from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    mcp,
)
from percival_research.metrics import log_query_safe
from percival_research.research_worker_client import (
    ProviderRejectedError,
    run_research_worker,
    validate_research_data,
)
from utils import (
    format_context_with_sources,
    handle_exception,
    new_correlation_id,
    sanitize_query,
    wrap_untrusted_content,
)

# ─────────────────────────────────────────────────────────────────────────────
# N7 fix (rodada 4): in-flight dedup map.
#
# Quando N tasks paralelas pedem o MESMO topic, em vez de rodar o pipeline
# completo N vezes (cada um ~30-60s + Tavily + LLM), todas as N aguardam
# a mesma Future compartilhada. Chave: `query` (após sanitize_topic).
#
# Estrutura thread-safe via `asyncio.Lock` — múltiplas tasks concorrentes
# entram na seção crítica só para criar/cancelar a Future compartilhada.
#
# Cleanup explícito no `finally` do bloco que define a Future.
# ─────────────────────────────────────────────────────────────────────────────
_IN_FLIGHT: dict[str, "asyncio.Future[str]"] = {}
_IN_FLIGHT_LOCK = asyncio.Lock()


@mcp.tool("research_deep")
async def deep_research(query: str, include_context: StrictBool = False) -> str:
    """Performs deep multi-source web research on a query and returns a summary with sources.

    Args:
        query: Topic to research.
        include_context: Strict bool (`True`/`False` only). Accepts
            neither int (`1`/`0`) nor string ('yes'/'no'/'true'/'false') —
            FastMCP framework coerces strings to bool in lax mode,
            inflating the response with untrusted context. Use a real
            boolean in the agent prompt.

    The server enforces `PERCIVAL_RESEARCH_TIMEOUT_S` (90 seconds by default).
    The matching Percival gateway candidate allows 180 seconds, the HTTP client
    allows 190 seconds, and the broker bounds long MCP calls at 150 seconds.
    Keep these transport budgets above the effective server deadline.
    """
    cid = new_correlation_id()

    # N9 (rodada 4 pós-fix): StrictBool annotation rejeita a chamada no
    # framework level (`bool_type Input should be a valid boolean`).
    # O isinstance abaixo é defesa em profundidade — em produção,
    # o erro do framework já é retornado antes do handler ser chamado.
    if not isinstance(include_context, bool):
        return (
            f"Error: include_context must be a boolean (got "
            f"{type(include_context).__name__}). (correlation_id={cid})"
        )

    try:
        query = sanitize_query(query)
    except ValueError as e:
        return f"Error: {str(e)} (correlation_id={cid})"

    log_query_safe("deep_research", query, cid)

    # Register atomically before admission. A waiter owns only its wait, not
    # the shared Future: cancelling a waiter must not cancel the creator.
    async with _IN_FLIGHT_LOCK:
        future = _IN_FLIGHT.get(query)
        is_creator = future is None
        if future is None:
            future = asyncio.get_running_loop().create_future()
            _IN_FLIGHT[query] = future
    if not is_creator:
        try:
            return await asyncio.shield(future)
        except Exception as exc:
            return handle_exception(exc, "Deep research (dedup waiter)", cid)

    acquired = False
    try:
        try:
            await _app.research_limiter.acquire()
            acquired = True
        except asyncio.TimeoutError:
            _app.metrics.record_timeout("deep_research")
            result = (
                "Error: Server is busy (concurrent research limit reached). "
                f"Try again in a few seconds. (correlation_id={cid})"
            )
            future.set_result(result)
            return result
        result = await _do_deep_research(query, include_context, cid)
        if not future.done():
            future.set_result(result)
        return result
    except asyncio.CancelledError:
        if not future.done():
            future.set_result(f"Error: Research was cancelled (correlation_id={cid}).")
        raise
    except Exception as exc:
        result = handle_exception(exc, "Deep research", cid)
        if not future.done():
            future.set_result(result)
        return result
    finally:
        if acquired:
            _app.research_limiter.release()
        # No await in cleanup: cancellation cannot interrupt ownership release.
        if _IN_FLIGHT.get(query) is future:
            _IN_FLIGHT.pop(query, None)


async def _do_deep_research(query: str, include_context: bool, cid: str) -> str:
    """Corpo principal do deep_research, separado para garantir que
    `release()` seja sempre chamado mesmo em caso de exceção.
    """
    start = time.monotonic()
    research_id = str(uuid.uuid4())
    timeout_s = _app._settings.research_timeout_s

    try:
        try:
            context, sources, source_urls = await run_research_worker(query, timeout_s)
        except ProviderRejectedError as exc:
            _app.metrics.record_error("deep_research")
            return f"Error: {exc} (correlation_id={cid})"
        except asyncio.TimeoutError:
            _app.metrics.record_timeout("deep_research")
            logger.error(f"[{cid}] deep_research timed out after {timeout_s}s")
            return (
                f"Error: Research exceeded the {timeout_s}s "
                f"internal limit (correlation_id={cid}). "
                f"Try a more specific query or increase PERCIVAL_RESEARCH_TIMEOUT_S."
            )

        validate_research_data(context, sources, source_urls)
        # The isolated worker cannot return its live network/client objects.
        # Rehydrate only the data needed by the public read/report tools.
        researcher = GPTResearcher(
            query=query,
            agent=UNIVERSAL_AGENT_NAME,
            role=_app._get_universal_agent_role(),
            verbose=False,
            context=context,
        )
        researcher.research_sources = sources
        researcher.visited_urls = set(source_urls)

        try:
            _app.registry.add_researcher(research_id, researcher)
        except Exception as add_err:
            # Audit rodada 2 BUG-5 — registry rejeita quando saturado.
            logger.error(f"[{cid}] add_researcher failed: {add_err}")
            _app.metrics.record_error("deep_research")
            return handle_exception(
                add_err,
                "Deep research (registry full)",
                cid,
            )

        logger.info(f"[{cid}] Research complete. ID: {research_id}")

        # `source_urls` pode ser None em algumas versões do gpt-researcher.
        # Garante lista antes de slicing.
        try:
            context = researcher.get_research_context()
            sources = researcher.get_research_sources() or []
            source_urls = researcher.get_source_urls() or []
        except Exception as e:
            # Em caso de falha ao extrair dados, evicta o researcher para
            # não segurar recursos (HTTP clients, contexto) até o TTL.
            _app.registry.evict_researcher(research_id)
            logger.error(f"[{cid}] Failed to extract research data: {e}")
            _app.metrics.record_error("deep_research")
            return handle_exception(e, "Deep research", cid)

        safe_formatted = wrap_untrusted_content(
            format_context_with_sources(query, context, sources)
        )
        _app.registry.store(query, context, sources, source_urls, safe_formatted)

        urls_preview = ", ".join(source_urls[:10])
        if len(source_urls) > 10:
            urls_preview += f" ... (+{len(source_urls) - 10} more)"

        # Audit rodada 3 BUG-3R-2: include safe_formatted no response
        # quando include_context=True (antes só context era incluído,
        # divergindo do que estava no cache).
        lines = [
            "Research complete.",
            f"research_id: {research_id}",
            f"query: {query}",
            f"source_count: {len(sources)}",
            f"source_urls: {urls_preview}",
        ]

        if include_context:
            lines.append("")
            lines.append(safe_formatted)

        lines.append("")
        lines.append(
            "Next steps: call write_report(research_id) to generate a full report, "
            "or get_research_context(research_id) to retrieve the synthesized context text."
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        _app.metrics.record_latency("deep_research", elapsed_ms)
        return "\n".join(lines)

    except Exception as e:
        # Em caso de erro genérico, evicta researcher do registry para
        # liberar recursos (HTTP clients, contexto carregado) imediatamente,
        # em vez de segurar até o TTL.
        try:
            _app.registry.evict_researcher(research_id)
        except Exception:
            pass  # id não estava registrado (ex.: erro antes de add_researcher)
        _app.metrics.record_error("deep_research")
        return handle_exception(e, "Deep research", cid)
