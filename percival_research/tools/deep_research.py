"""Tool: deep_research — pesquisa profunda multi-fonte."""

import asyncio
import sys
import time
import uuid
from contextlib import redirect_stdout

from gpt_researcher import GPTResearcher
from loguru import logger
from pydantic import StrictBool

from percival_research.app import (
    UNIVERSAL_AGENT_NAME,
    mcp,
    metrics,
)
import percival_research.app as _app
from utils import (
    format_context_with_sources,
    handle_exception,
    new_correlation_id,
    sanitize_query,
    wrap_untrusted_content,
)
from percival_research.metrics import log_query_safe


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


async def _acquire_in_flight_slot(query: str) -> tuple["asyncio.Future[str] | None", str]:
    """Tenta reservar uma in-flight slot para `query`.

    Returns:
        (future, slot_status):
        - (None, "caller_creates"): caller deve criar a Future e popular
          o dict antes de qualquer outra task entrar.
        - (existing_future, "shared"): já existe um task rodando o
          mesmo `query`; caller deve `await` a Future retornada.
    """
    async with _IN_FLIGHT_LOCK:
        if query in _IN_FLIGHT:
            return _IN_FLIGHT[query], "shared"
    return None, "caller_creates"


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

    # N7 fix (rodada 4): in-flight dedup ANTES do rate-limiter. Se outro
    # task já está rodando o mesmo topic, recuperamos a Future compartilhada
    # e esperamos — economiza um slot do rate-limiter E o pipeline completo.
    existing, status = await _acquire_in_flight_slot(query)
    if existing is not None:
        logger.info(
            f"[{cid}] deep_research dedup hit — waiting for "
            f"in-flight task (status={status})"
        )
        return await existing

    # Caller_creates path: registramos a Future neste slot.
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    async def _register():
        async with _IN_FLIGHT_LOCK:
            # Double-check: outra task pode ter inserido entre o check
            # acima e o lock (race window). Se sim, retornamos a dela.
            if query in _IN_FLIGHT:
                return _IN_FLIGHT[query], False
            _IN_FLIGHT[query] = future
            return future, True

    shared_or_ours, is_creator = await _register()
    if not is_creator:
        return await shared_or_ours

    # Audit rodada 2 BUG-7: RateLimiter.acquire tem timeout (30s default).
    # Audit rodada 3 BUG-3R-3/5: try/finally para release() em TODOS os
    # caminhos (incluindo sucesso, timeout de pesquisa, exception genérica).
    # Antes, release() nunca era chamado → slots vazavam.
    try:
        await _app.research_limiter.acquire()
    except asyncio.TimeoutError:
        # Liberar a slot de in-flight — caller não vai rodar.
        async with _IN_FLIGHT_LOCK:
            _IN_FLIGHT.pop(query, None)
        if not future.done():
            future.set_exception(
                RuntimeError(
                    "deep_research cancelled before pipeline started "
                    "(server busy)"
                )
            )
        # S3 fix (roda 5): sem este consume explícito, o Python log
        # "Future exception was never retrieved" toda vez que o rate
        # limiter rejeita. Agora consumimos para limpeza de warning.
        future.exception()
        metrics.record_timeout("deep_research")
        logger.warning(f"[{cid}] rate limit acquire timeout")
        return (
            f"Error: Server is busy (concurrent research limit reached). "
            f"Try again in a few seconds. (correlation_id={cid})"
        )

    try:
        result = await _do_deep_research(query, include_context, cid)
        if not future.done():
            future.set_result(result)
        return result
    except Exception as exc:
        if not future.done():
            future.set_exception(exc)
        raise
    finally:
        _app.research_limiter.release()
        # Remove a in-flight slot DEPOIS de set_result/set_exception.
        # Waiters que chegam durante o cleanup vão pegar a Future
        # existente e ainda assim receber o resultado (a Future não é
        # cancelada).
        async with _IN_FLIGHT_LOCK:
            if _IN_FLIGHT.get(query) is future:
                _IN_FLIGHT.pop(query, None)


async def _do_deep_research(query: str, include_context: bool, cid: str) -> str:
    """Corpo principal do deep_research, separado para garantir que
    `release()` seja sempre chamado mesmo em caso de exceção.
    """
    start = time.monotonic()
    research_id = str(uuid.uuid4())
    researcher = GPTResearcher(
        query=query,
        agent=UNIVERSAL_AGENT_NAME,
        role=_app._get_universal_agent_role(),  # dinâmico (audit rodada 2)
        verbose=False,
    )

    timeout_s = _app._settings.research_timeout_s

    async def _do_research():
        with redirect_stdout(sys.stderr):
            await researcher.conduct_research()

    try:
        try:
            await asyncio.wait_for(_do_research(), timeout=timeout_s)
        except asyncio.TimeoutError:
            metrics.record_timeout("deep_research")
            logger.error(f"[{cid}] deep_research timed out after {timeout_s}s")
            return (
                f"Error: Research exceeded the {timeout_s}s "
                f"internal limit (correlation_id={cid}). "
                f"Try a more specific query or increase PERCIVAL_RESEARCH_TIMEOUT_S."
            )

        try:
            _app.registry.add_researcher(research_id, researcher)
        except Exception as add_err:
            # Audit rodada 2 BUG-5 — registry rejeita quando saturado.
            logger.error(f"[{cid}] add_researcher failed: {add_err}")
            metrics.record_error("deep_research")
            return handle_exception(
                add_err, "Deep research (registry full)", cid,
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
            metrics.record_error("deep_research")
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
        metrics.record_latency("deep_research", elapsed_ms)
        return "\n".join(lines)

    except Exception as e:
        # Em caso de erro genérico, evicta researcher do registry para
        # liberar recursos (HTTP clients, contexto carregado) imediatamente,
        # em vez de segurar até o TTL.
        try:
            _app.registry.evict_researcher(research_id)
        except Exception:
            pass  # id não estava registrado (ex.: erro antes de add_researcher)
        metrics.record_error("deep_research")
        return handle_exception(e, "Deep research", cid)