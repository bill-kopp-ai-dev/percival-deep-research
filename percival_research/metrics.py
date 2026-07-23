"""Métricas: log_query_safe + endpoint /metrics.

A classe `Metrics` em si vive em `utils.py` (histórico); este módulo
exporta a função utilitária `log_query_safe` e o endpoint HTTP.
"""

import os

from fastapi.responses import JSONResponse
from loguru import logger

from percival_research.app import mcp, metrics as _global_metrics


def log_query_safe(operation: str, query: str, cid: str) -> None:
    """Loga a operação com um preview sanitizado da query (sem PII).

    Audit rodada 3 BUG-3R-1: `PERCIVAL_DEBUG_LOG_QUERIES` é lido em
    CADA chamada (não no import-time como era antes), permitindo
    que testes e operadores modifiquem o toggle em runtime.
    """
    debug = os.getenv("PERCIVAL_DEBUG_LOG_QUERIES", "false").lower() == "true"
    if debug:
        logger.debug(f"[{cid}] {operation} query={query!r}")
    else:
        preview = query[:80].replace("\n", " ")
        logger.info(f"[{cid}] {operation} starting — preview={preview!r}…")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics_endpoint(request):
    return JSONResponse(_global_metrics.snapshot())