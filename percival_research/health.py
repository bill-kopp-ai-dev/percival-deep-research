"""Health check endpoint."""

import os

from fastapi.responses import JSONResponse

from percival_research.app import mcp


def _check_openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"))


def _check_retriever_configured() -> bool:
    return bool(os.getenv("RETRIEVER")) or bool(os.getenv("BRAVE_API_KEY"))


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    openai_ok = _check_openai_configured()
    retriever_ok = _check_retriever_configured()
    healthy = openai_ok and retriever_ok
    body = {
        "status": "healthy" if healthy else "degraded",
        "service": "gptr-mcp",
        "checks": {
            "openai_configured": openai_ok,
            "retriever_configured": retriever_ok,
        },
    }
    return JSONResponse(body, status_code=200 if healthy else 503)