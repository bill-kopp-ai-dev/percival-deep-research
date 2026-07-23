"""Plugin layer para retrievers (Fase 7).

Esta camada **não é usada diretamente** pelo `gpt-researcher` — ela
documenta a interface `Retriever` para futuras integrações onde o
servidor pode usar o retriever independentemente (ex: tool
`quick_search` customizada).
"""

from typing import Protocol, Callable


class Retriever(Protocol):
    """Interface mínima que qualquer retriever deve implementar."""

    name: str

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Retorna lista de dicts com chaves: title, url, content, snippet."""
        ...

    async def close(self) -> None:
        """Cleanup opcional (ex: fechar HTTP client)."""
        ...


_REGISTRY: dict = {}


def register_retriever(name: str, cls: type) -> None:
    """Decorator / função para registrar um retriever custom."""
    _REGISTRY[name] = cls


def get_retriever(name: str, **kwargs) -> Retriever:
    """Resolve e instancia um retriever pelo nome."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown retriever: {name!r}. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](**kwargs)


# Built-ins (carregados lazy; sem dependências externas obrigatórias)
from . import duckduckgo as _ddg  # noqa: E402, F401
from . import brave as _brave  # noqa: E402, F401

__all__ = ["Retriever", "register_retriever", "get_retriever"]