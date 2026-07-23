"""Health check endpoint."""

import os

from fastapi.responses import JSONResponse

from percival_research.app import mcp


def _check_openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"))


def _check_retriever_configured() -> bool:
    """Valida que o(s) retriever(s) configurado(s) têm as credenciais necessárias.

    Bug encontrado na revisão pós-refactor: a versão anterior fazia
    `bool(os.getenv("RETRIEVER")) or bool(os.getenv("BRAVE_API_KEY"))`,
    o que reporta "healthy" sempre que `RETRIEVER` está setado — mesmo
    com `RETRIEVER=brave` (o default deste projeto, ver `.env.example`)
    e `BRAVE_API_KEY` ausente. Isso é exatamente o falso-positivo que o
    HIGH-04 (health check real) deveria eliminar: `deep_research`/
    `quick_search` falhariam em toda chamada, mas `/health` diria 200.

    `RETRIEVER` aceita lista separada por vírgula (suportado pelo
    gpt-researcher para fallback entre múltiplos retrievers); só exige
    `BRAVE_API_KEY` quando "brave" está entre os retrievers ativos.
    """
    raw = os.getenv("RETRIEVER", "brave")
    retrievers = [r.strip().lower() for r in raw.split(",") if r.strip()]
    if "brave" in retrievers:
        return bool(os.getenv("BRAVE_API_KEY"))
    return True


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