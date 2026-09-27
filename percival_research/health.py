"""Health check endpoint."""

import os

from fastapi.responses import JSONResponse

from percival_research import __version__
from percival_research.app import mcp


def _check_inference_configured() -> bool:
    """v2.2: lê `INFERENCE_API_KEY` (canônico), com fallback para
    `OPENAI_API_KEY` (deprecated). Retorna True se QUALQUER um estiver
    setado. Não verifica validade real da chave (assim como a versão
    anterior)."""
    return bool(
        os.getenv("INFERENCE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("INFERENCE_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )


def _check_retriever_configured() -> bool:
    """Valida que o(s) retriever(s) configurado(s) têm as credenciais necessárias.

    v2.2: default é `duckduckgo` (sem chave). Brave continua funcionando
    se for explicitamente listado em `RETRIEVER` (com `BRAVE_API_KEY`
    setada). Lista separada por vírgula suportada (fallback entre
    múltiplos retrievers).

    Round 6 fix (bug-hunt): antes qualquer retriever não-"brave" era
    implicitamente tratado como "OK" (sem credencial necessária). Agora
    valida contra o registry de retrievers conhecidos — um typo
    (`RETRIEVER=bing`) falha em vez de reportar "healthy" mentirosamente.
    """
    raw = os.getenv("RETRIEVER", "duckduckgo")
    retrievers = [r.strip().lower() for r in raw.split(",") if r.strip()]
    if not retrievers:
        return False

    # Lazy import: registry é populado por side-effect em retrievers/__init__.py
    try:
        from percival_research.retrievers import _REGISTRY
    except ImportError:
        _REGISTRY = {}

    for name in retrievers:
        if name == "brave":
            if not bool(os.getenv("BRAVE_API_KEY")):
                return False
        elif name not in _REGISTRY:
            # Retriever desconhecido — health-check deve falhar para o
            # operador ver o problema em vez de descobrir só em runtime.
            return False
        # Outros retrievers registrados não exigem API key
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
        "version": __version__,
        "checks": {
            "inference_configured": inference_ok,
            "retriever_configured": retriever_ok,
        },
    }
    return JSONResponse(body, status_code=200 if healthy else 503)
