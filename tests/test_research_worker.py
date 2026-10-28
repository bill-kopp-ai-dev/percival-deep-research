"""Tests for the isolated research worker process."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

STUB_GPT_RESEARCHER = """
class GPTResearcher:
    def __init__(self, query, agent=None, role=None, verbose=False, context=None, **kwargs):
        self.query = query
        self.context = context or []

    async def conduct_research(self):
        self.context = [{"title": "Stub", "content": "contexto sintetizado"}]
        print("upstream chatter on stdout")

    def get_research_context(self):
        return self.context

    def get_research_sources(self):
        return [{"title": "Fixture", "url": "https://fixture.example/a", "raw_content": "abcde"}]

    def get_source_urls(self):
        return ["https://fixture.example/a"]
"""


def _run_worker(tmp_path: Path, stdin_payload: str) -> subprocess.CompletedProcess:
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "gpt_researcher.py").write_text(textwrap.dedent(STUB_GPT_RESEARCHER))
    return subprocess.run(
        [sys.executable, "-m", "percival_research.research_worker"],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": f"{stub_dir}:{Path(__file__).resolve().parents[1]}",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        timeout=120,
    )


def test_worker_returns_structured_payload(tmp_path):
    """The worker answers with JSON carrying context, sources and URLs."""
    result = _run_worker(tmp_path, json.dumps({"query": "fixture"}))

    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    assert payload["context"] == [{"title": "Stub", "content": "contexto sintetizado"}]
    assert payload["sources"][0]["raw_content"] == "abcde"
    assert payload["source_urls"] == ["https://fixture.example/a"]


def test_worker_keeps_stdout_clean_for_protocol(tmp_path):
    """Upstream chatter on stdout must not corrupt the JSON protocol."""
    result = _run_worker(tmp_path, json.dumps({"query": "fixture"}))

    assert result.returncode == 0, result.stderr[-2000:]
    json.loads(result.stdout)


def test_worker_fails_without_revealing_internals(tmp_path):
    """A worker failure exits non-zero and does not echo the request."""
    result = _run_worker(tmp_path, "not-json-at-all")

    assert result.returncode != 0
    assert "not-json-at-all" not in result.stdout
