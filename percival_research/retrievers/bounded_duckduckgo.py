"""Single-backend DDG retriever with an explicit per-request deadline."""

from __future__ import annotations

import sys
import time

from ddgs import DDGS

_SEARCH_TIMEOUT_S = 5


class BoundedDuckduckgo:
    """Replace ddgs' multi-provider ``auto`` fan-out with one bounded engine.

    ddgs' ``auto`` backend waits for concurrent providers in sequential batches;
    slow unfinished work is joined when its executor exits. This is multiplied
    across every planned sub-query and can consume the full research deadline.
    A single provider plus its own socket timeout makes each search duration
    predictable and leaves the research deadline for synthesis/scraping.
    """

    def __init__(self, query: str, query_domains: list[str] | None = None):
        self.query = query
        self.query_domains = query_domains or None

    def search(self, max_results: int = 5) -> list[dict[str, str]]:
        started = time.monotonic()
        print("PERCIVAL_STAGE search_engine", file=sys.stderr, flush=True)
        try:
            with DDGS(timeout=_SEARCH_TIMEOUT_S) as client:
                results = client.text(
                    self.query,
                    region="wt-wt",
                    max_results=max_results,
                    backend="duckduckgo",
                )
        except Exception as exc:
            # Do not echo request/query, response bodies or provider exception
            # contents: only type and duration are useful and safe to retain.
            print(
                f"PERCIVAL_SEARCH outcome=error error_type={type(exc).__name__} "
                f"elapsed_ms={int((time.monotonic() - started) * 1000)}",
                file=sys.stderr,
                flush=True,
            )
            raise

        normalized: list[dict[str, str]] = []
        for result in results or []:
            if not isinstance(result, dict):
                continue
            url = result.get("href") or result.get("link") or result.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                continue
            body = result.get("body") or result.get("snippet") or result.get("description") or ""
            item = {"href": url, "body": str(body)}
            title = result.get("title")
            if isinstance(title, str) and title:
                item["title"] = title
            normalized.append(item)
            if len(normalized) >= max_results:
                break
        print(
            f"PERCIVAL_SEARCH outcome=complete results={len(normalized)} "
            f"elapsed_ms={int((time.monotonic() - started) * 1000)}",
            file=sys.stderr,
            flush=True,
        )
        return normalized


def install_bounded_retrievers(researcher) -> None:
    """Replace only the configured upstream DuckDuckGo engine on one instance."""
    retrievers = getattr(researcher, "retrievers", None)
    if not isinstance(retrievers, list):
        return
    researcher.retrievers = [
        BoundedDuckduckgo if getattr(item, "__name__", "").lower() == "duckduckgo" else item
        for item in retrievers
    ]
