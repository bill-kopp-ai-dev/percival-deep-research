"""Tool: write_report — gera relatório estruturado de uma sessão de pesquisa."""

import asyncio
import time

from loguru import logger

import percival_research.app as _app
from percival_research.app import mcp
from percival_research.research_worker_client import ProviderRejectedError, run_report_worker
from utils import (
    handle_exception,
    new_correlation_id,
    sanitize_prompt,
    validate_research_id,
)


@mcp.tool("research_write_report")
async def write_report(research_id: str, custom_prompt: str | None = None) -> str:
    """Generates a structured Markdown report from an existing research session."""
    cid = new_correlation_id()
    if not validate_research_id(research_id):
        return f"Error: Invalid research_id. Provide a valid UUID obtained from deep_research. (correlation_id={cid})"

    if custom_prompt is not None:
        try:
            custom_prompt = sanitize_prompt(custom_prompt)
        except ValueError as e:
            return f"Error: Invalid custom_prompt: {str(e)} (correlation_id={cid})"

    success, researcher, error = _app.registry.get_researcher(research_id)
    if not success:
        msg = error.get("message", "Research session not found or expired.")
        return f"Error: {msg} (correlation_id={cid})"

    logger.info(f"[{cid}] Generating report for ID: {research_id}")

    start = time.monotonic()
    try:
        report = await run_report_worker(
            researcher.query,
            researcher.get_research_context(),
            researcher.get_research_sources() or [],
            researcher.get_source_urls() or [],
            custom_prompt,
            _app._settings.research_timeout_s,
        )

        lines = ["", report]
        return "\n".join(lines)

    except ProviderRejectedError as exc:
        _app.metrics.record_error("write_report")
        return f"Error: {exc} (correlation_id={cid}). Research session remains available."
    except asyncio.TimeoutError:
        _app.metrics.record_timeout("write_report")
        return (
            f"Error: Report exceeded the {_app._settings.research_timeout_s}s "
            f"internal limit (correlation_id={cid}). Research session remains available."
        )
    except Exception as e:
        # The isolated report owns its resources. Keep the successful research
        # session so a report failure never forces a paid repeat of research.
        _app.metrics.record_error("write_report")
        return handle_exception(e, "Report generation", cid)
    finally:
        # Round 6 fix (bug-hunt): antes, `write_report_total` nunca era
        # incrementado (só erros eram registrados via record_error).
        # Agora o caminho de sucesso também alimenta o counter e o deque
        # de latências, alinhando `/metrics` com a realidade do tráfego.
        # Usa `_app.metrics` (lookup em runtime) em vez de `metrics`
        # capturado no import, para honrar patches em testes
        # (ex.: `clean_app_state` em conftest).
        elapsed_ms = (time.monotonic() - start) * 1000
        _app.metrics.record_latency("write_report", elapsed_ms)
