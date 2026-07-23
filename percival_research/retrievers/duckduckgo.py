"""Retriever DuckDuckGo (default, sem chave de API)."""

from . import register_retriever


class DuckDuckGoRetriever:
    name = "duckduckgo"

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        try:
            from duckduckgo_search import DDGS
        except ImportError as exc:
            raise RuntimeError(
                "duckduckgo-search não instalado. Use brave ou instale "
                "duckduckgo-search: `uv pip install duckduckgo-search`"
            ) from exc

        with DDGS() as ddgs:
            return [
                {
                    "title": r["title"],
                    "url": r["href"],
                    "content": r["body"],
                    "snippet": r["body"][:200],
                }
                for r in ddgs.text(query, max_results=max_results)
            ]

    async def close(self) -> None:
        pass


register_retriever("duckduckgo", DuckDuckGoRetriever)