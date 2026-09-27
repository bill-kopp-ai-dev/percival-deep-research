"""Tool: write_report — gera relatório estruturado de uma sessão de pesquisa."""

import sys
import time
from contextlib import redirect_stdout

from loguru import logger

import percival_research.app as _app
from percival_research.app import mcp
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
        with redirect_stdout(sys.stderr):
            report = await researcher.write_report(custom_prompt=custom_prompt)

        lines = ["", report]
        return "\n".join(lines)

    except Exception as e:
        # Em caso de erro, evicta o researcher para liberar recursos.
        try:
            _app.registry.evict_researcher(research_id)
        except Exception:
            pass
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
