"""Health check endpoint."""

import inspect
import os
import re

from fastapi.responses import JSONResponse

from percival_research import __version__
from percival_research.app import mcp

_ENV_ACCESS = re.compile(r"""os\.environ\[\s*['"]([A-Z0-9_]+)['"]\s*\]""")


def _check_inference_configured() -> bool:
    """v2.2: lê `INFERENCE_API_KEY` (canônico), com fallback para
    `OPENAI_API_KEY` (deprecated). Retorna True se QUALQUER um estiver
    setado. Não verifica validade real da chave (assim como a versão
    anterior).

    Additionally, a malformed `INFERENCE_LLM` (no `provider:model` shape or
    an unexpanded `${...}` placeholder) marks the configuration invalid: the
    upstream only fails later, on the first provider call.
    """
    has_endpoint_or_key = bool(
        os.getenv("INFERENCE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("INFERENCE_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )
    if not has_endpoint_or_key:
        return False

    llm = os.getenv("INFERENCE_LLM", "")
    if llm and (":" not in llm or not all(llm.split(":", 1)) or any(c in llm for c in "${}")):
        return False
    return True


def _required_env_for_retriever(retriever_cls) -> list[str]:
    """Environment variables the upstream retriever reads as mandatory.

    The upstream retrievers read their credentials through
    `os.environ["NAME"]`, which raises `KeyError` when unset. Reading the
    installed module keeps this list aligned with the pinned upstream instead
    of hardcoding a list that can drift.
    """
    try:
        source = inspect.getsource(retriever_cls)
    except (OSError, TypeError):
        return []
    return sorted(set(_ENV_ACCESS.findall(source)))


def _check_retriever_configured() -> bool:
    """Valida que o(s) retriever(s) configurado(s) existem no upstream e
    têm as credenciais necessárias.

    A lista de retrievers válidos vem do registry do gpt-researcher embarcado
    (`gpt_researcher.actions.retriever.get_retriever`). As variáveis de
    ambiente obrigatórias são lidas do módulo upstream instalado, para que um
    `SEARX_URL` ou `TAVILY_API_KEY` ausente degrade o health-check em vez de
    falhar na primeira chamada.

    O endpoint valida suporte/configuração, não conectividade com o provedor.
    """
    raw = os.getenv("RETRIEVER", "duckduckgo")
    retrievers = [r.strip().lower() for r in raw.split(",") if r.strip()]
    if not retrievers:
        return False

    try:
        from gpt_researcher.actions.retriever import get_retriever
    except ImportError:
        return False

    for name in retrievers:
        try:
            retriever_cls = get_retriever(name)
        except (ImportError, AttributeError, ValueError):
            retriever_cls = None
        if retriever_cls is None:
            # Um typo ou provider indisponível na instalação deve degradar.
            return False
        for env_var in _required_env_for_retriever(retriever_cls):
            if not os.getenv(env_var):
                return False
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
