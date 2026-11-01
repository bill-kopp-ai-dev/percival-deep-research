"""The default retriever makes one bounded upstream request per query."""

from types import SimpleNamespace

from percival_research.retrievers import bounded_duckduckgo as retriever


def test_bounded_retriever_uses_single_backend_and_normalizes_results(monkeypatch):
    observed = {}

    class FakeDDGS:
        def __init__(self, *, timeout):
            observed["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def text(self, query, **kwargs):
            observed["query"] = query
            observed.update(kwargs)
            return [
                {
                    "link": "https://docs.python.org/3/library/asyncio-task.html",
                    "title": "Tasks",
                    "snippet": "Cancellation",
                },
                {"url": "javascript:alert(1)", "description": "invalid URL"},
            ]

    monkeypatch.setattr(retriever, "DDGS", FakeDDGS)
    result = retriever.BoundedDuckduckgo("public fixture").search(max_results=3)
    assert observed == {
        "timeout": 5,
        "query": "public fixture",
        "region": "wt-wt",
        "max_results": 3,
        "backend": "duckduckgo",
    }
    assert result == [
        {
            "href": "https://docs.python.org/3/library/asyncio-task.html",
            "body": "Cancellation",
            "title": "Tasks",
        }
    ]


def test_install_replaces_only_default_duckduckgo_engine():
    from percival_research.retrievers.bounded_duckduckgo import (
        BoundedDuckduckgo,
        install_bounded_retrievers,
    )

    duckduckgo = type("Duckduckgo", (), {})
    brave = type("Brave", (), {})
    researcher = SimpleNamespace(retrievers=[duckduckgo, brave])
    install_bounded_retrievers(researcher)
    assert researcher.retrievers == [BoundedDuckduckgo, brave]


def test_backend_timeout_failure_does_not_fan_out_or_retry(monkeypatch):
    observed = {"calls": 0}

    class TimedOutDDGS:
        def __init__(self, *, timeout):
            assert timeout == 5

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def text(self, _query, **kwargs):
            observed["calls"] += 1
            assert kwargs["backend"] == "duckduckgo"
            raise TimeoutError("fixture timeout")

    monkeypatch.setattr(retriever, "DDGS", TimedOutDDGS)
    try:
        retriever.BoundedDuckduckgo("public fixture").search()
    except TimeoutError:
        pass
    else:
        raise AssertionError("timeout should remain visible to the caller")
    assert observed["calls"] == 1
