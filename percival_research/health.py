"""Health check endpoint."""

import os

from fastapi.responses import JSONResponse

from percival_research.app import mcp


def _check_inference_configured() -> bool:
    """v2.2: lê `INFERENCE_API_KEY` (canônico), com fallback para
    `OPENAI_API_KEY` (deprecated). Retorna True se QUALQUER um estiver
    setado. Não verifica validade real da chave (assim como a versão
    anterior)."""
    return bool(
        os.getenv("INFERENCE_API_KEY") or os.getenv("OPENAI_API_KEY")
        or os.getenv("INFERENCE_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    )


def _check_retriever_configured() -> bool:
    """Valida que o(s) retriever(s) configurado(s) têm as credenciais necessárias.

    v2.2: default é `duckduckgo` (sem chave). Brave continua funcionando
    se for explicitamente listado em `RETRIEVER` (com `BRAVE_API_KEY`
    setada). Lista separada por vírgula suportada (fallback entre
    múltiplos retrievers).
    """
    raw = os.getenv("RETRIEVER", "duckduckgo")
    retrievers = [r.strip().lower() for r in raw.split(",") if r.strip()]
    if "brave" in retrievers:
        return bool(os.getenv("BRAVE_API_KEY"))
    # duckduckgo (e outros) não exigem API key
    return True


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health endpoint (v2.2).

    Schema do response:
        {
          "status": "healthy" | "degraded",
          "service": "gptr-mcp",
          "version": "2.2.0",
          "checks": {
            "inference_configured": bool,   # INFERENCE_API_KEY ou OPENAI_API_KEY
            "retriever_configured": bool    # RETRIEVER xxx sem credenciais necessárias
          }
        }

    HTTP 200 se tudo OK, 503 se qualquer check falhar.
    """
    inference_ok = _check_inference_configured()
    retriever_ok = _check_retriever_configured()
    healthy = inference_ok and retriever_ok
    body = {
        "status": "healthy" if healthy else "degraded",
        "service": "gptr-mcp",
        "version": "2.2.0",
        "checks": {
            "inference_configured": inference_ok,
            "retriever_configured": retriever_ok,
        },
    }
    return JSONResponse(body, status_code=200 if healthy else 503)