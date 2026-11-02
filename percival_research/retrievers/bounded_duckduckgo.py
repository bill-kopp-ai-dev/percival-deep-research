"""Bounded search with explicit engines and a small deterministic fallback."""

from __future__ import annotations

import sys
import time

from ddgs import DDGS
from ddgs.engines import ENGINES
from ddgs.exceptions import DDGSException

_SEARCH_TIMEOUT_S = 5
_BACKENDS = ("duckduckgo", "yahoo")


class BoundedDuckduckgo:
    """Replace ddgs' multi-provider ``auto`` fan-out with bounded attempts.

    ddgs' ``auto`` backend waits for concurrent providers in sequential batches;
    slow unfinished work is joined when its executor exits. This is multiplied
    across every planned sub-query and can consume the full research deadline.
    Each attempt uses exactly one engine and its own socket timeout. A second
    engine handles DDG's bot challenges/no-results without an unbounded fan-out.
    The isolated worker provides the hard deadline for the entire pipeline.
    """

    def __init__(self, query: str, query_domains: list[str] | None = None):
        self.query = query
        self.query_domains = query_domains or None

    def search(self, max_results: int = 5) -> list[dict[str, str]]:
        print("PERCIVAL_STAGE search_engine", file=sys.stderr, flush=True)
        last_error = None
        for backend in _BACKENDS:
            # ddgs silently falls back to `auto` for disabled/missing engines.
            # Reject that path before dispatch so the attempt count stays bounded.
            if backend not in ENGINES["text"]:
                raise RuntimeError("Required bounded search backend is unavailable")
            started = time.monotonic()
            try:
                with DDGS(timeout=_SEARCH_TIMEOUT_S) as client:
                    results = client.text(
                        self.query,
                        region="us-en",
                        max_results=max_results,
                        backend=backend,
                    )
            except Exception as exc:
                # Never echo queries, response bodies or provider exception text.
                print(
                    f"PERCIVAL_SEARCH backend={backend} outcome=error "
                    f"error_type={type(exc).__name__} "
                    f"elapsed_ms={int((time.monotonic() - started) * 1000)}",
                    file=sys.stderr,
                    flush=True,
                )
                # ddgs uses an exception for an empty search. Allow planning to
                # formulate better subqueries, but never hide transport failures.
                if type(exc) is DDGSException and str(exc) == "No results found.":
                    continue
                last_error = exc
                continue

            normalized: list[dict[str, str]] = []
            for result in results or []:
                if not isinstance(result, dict):
                    continue
                url = result.get("href") or result.get("link") or result.get("url")
                if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                    continue
                body = (
                    result.get("body") or result.get("snippet") or result.get("description") or ""
                )
                item = {"href": url, "body": str(body)}
                title = result.get("title")
                if isinstance(title, str) and title:
                    item["title"] = title
                normalized.append(item)
                if len(normalized) >= max_results:
                    break
            print(
                f"PERCIVAL_SEARCH backend={backend} outcome=complete results={len(normalized)} "
                f"elapsed_ms={int((time.monotonic() - started) * 1000)}",
                file=sys.stderr,
                flush=True,
            )
            if normalized:
                print("PERCIVAL_STAGE search_complete", file=sys.stderr, flush=True)
                return normalized
        if last_error is not None:
            raise last_error
        return []


def install_bounded_retrievers(researcher) -> None:
    """Replace only the configured upstream DuckDuckGo engine on one instance."""
    retrievers = getattr(researcher, "retrievers", None)
    if not isinstance(retrievers, list):
        return
    researcher.retrievers = [
        BoundedDuckduckgo if getattr(item, "__name__", "").lower() == "duckduckgo" else item
        for item in retrievers
    ]
