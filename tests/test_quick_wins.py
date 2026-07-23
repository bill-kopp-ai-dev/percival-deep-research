"""Testes da Fase 1 — quick wins."""

import uuid as _uuid

from utils import (
    format_sources_lines,
    handle_exception,
    new_correlation_id,
)


def test_correlation_id_format():
    cid = new_correlation_id()
    assert cid.startswith("crl-")
    assert len(cid) == 12  # "crl-" + 8 hex


def test_correlation_id_unico():
    """Cada chamada deve gerar ID distinto."""
    ids = {new_correlation_id() for _ in range(100)}
    assert len(ids) == 100


def test_handle_exception_includes_correlation_id():
    err = RuntimeError("segredo interno sk-proj-abc123")
    result = handle_exception(err, "TestOp")
    assert result.startswith("Error:")
    assert "correlation_id=" in result
    # Segredo não vaza
    assert "segredo interno" not in result
    assert "sk-proj-abc123" not in result
    # Operação é citada
    assert "TestOp" in result


def test_handle_exception_with_explicit_correlation_id():
    err = RuntimeError("segredo")
    result = handle_exception(err, "TestOp", correlation_id="crl-fixed01")
    assert "crl-fixed01" in result


def test_handle_exception_generates_id_when_not_provided():
    err = RuntimeError("x")
    r1 = handle_exception(err, "TestOp")
    r2 = handle_exception(err, "TestOp")
    # IDs diferentes a cada chamada
    cid1 = r1.split("correlation_id=")[1].split(")")[0]
    cid2 = r2.split("correlation_id=")[1].split(")")[0]
    assert cid1 != cid2


def test_format_sources_lines_basic():
    formatted = [
        {"title": "Doc", "url": "https://a.com", "content_length": 42},
    ]
    lines = format_sources_lines(formatted)
    assert lines == ["[1] Doc | https://a.com | 42 chars"]


def test_format_sources_lines_handles_missing_title():
    formatted = [{"url": "https://a.com", "content_length": 0}]
    lines = format_sources_lines(formatted)
    assert lines == ["[1] Unknown | https://a.com | 0 chars"]


def test_format_sources_lines_handles_missing_url():
    formatted = [{"title": "T", "content_length": 5}]
    lines = format_sources_lines(formatted)
    assert lines == ["[1] T |  | 5 chars"]


def test_format_sources_lines_empty():
    assert format_sources_lines([]) == []


def test_format_sources_lines_multiple():
    formatted = [
        {"title": "A", "url": "u1", "content_length": 1},
        {"title": "B", "url": "u2", "content_length": 2},
        {"title": "C", "url": "u3", "content_length": 3},
    ]
    lines = format_sources_lines(formatted)
    assert lines == [
        "[1] A | u1 | 1 chars",
        "[2] B | u2 | 2 chars",
        "[3] C | u3 | 3 chars",
    ]


def test_validate_research_id_aceita_v1():
    """UUID v1 deve ser aceito (Fase 1: aceitar qualquer versão RFC 4122)."""
    from server import _validate_research_id
    v1 = str(_uuid.uuid1())
    assert _validate_research_id(v1) is True


def test_validate_research_id_aceita_v4():
    from server import _validate_research_id
    assert _validate_research_id(str(_uuid.uuid4())) is True


def test_validate_research_id_aceita_v3():
    """UUID v3 (MD5 namespace) deve ser aceito."""
    from server import _validate_research_id
    v3 = str(_uuid.uuid3(_uuid.NAMESPACE_DNS, "example.com"))
    assert _validate_research_id(v3) is True


def test_validate_research_id_rejeita_path_traversal():
    from server import _validate_research_id
    assert _validate_research_id("../../etc/passwd") is False


def test_validate_research_id_rejeita_vazio():
    from server import _validate_research_id
    assert _validate_research_id("") is False


def test_validate_research_id_rejeita_lixo():
    from server import _validate_research_id
    assert _validate_research_id("not-a-uuid") is False