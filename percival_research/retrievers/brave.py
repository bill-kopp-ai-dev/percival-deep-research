"""Retriever Brave Search (requer BRAVE_API_KEY)."""

import os

from . import register_retriever


class BraveRetriever:
    name = "brave"

    def __init__(self, api_key: str | None = None, **kwargs):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY required for brave retriever")
        import httpx  # lazy import
        self._client = httpx.AsyncClient(
            base_url="https://api.search.brave.com",
            headers={"X-Subscription-Token": self.api_key},
            timeout=30,
        )

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        resp = await self._client.get(
            "/res/v1/web/search",
            params={"q": query, "count": max_results},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "content": r.get("description", ""),
                "snippet": r.get("description", "")[:200],
            }
            for r in data.get("web", {}).get("results", [])
        ]

    async def close(self) -> None:
        await self._client.aclose()


register_retriever("brave", BraveRetriever)