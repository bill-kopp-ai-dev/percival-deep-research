"""Testes da Fase 5 — coverage de tools: get_research_context e get_research_sources."""

import uuid

import pytest

from percival_research.tools.deep_research import deep_research
from percival_research.tools.get_research_context import get_research_context
from percival_research.tools.get_research_sources import get_research_sources


# ── get_research_context ─────────────────────────────────

@pytest.mark.asyncio
async def test_get_research_context_sucesso(clean_app_state, mock_gpt_researcher):
    summary = await deep_research("topic")
    research_id = summary.split("research_id: ")[1].split("\n")[0]

    result = await get_research_context(research_id)

    assert "SECURITY WARNING" in result
    assert "Contexto sintetizado." in result


@pytest.mark.asyncio
async def test_get_research_context_uuid_invalido():
    result = await get_research_context("../../../etc/passwd")

    assert result.startswith("Error:")
    assert "Invalid research_id" in result


@pytest.mark.asyncio
async def test_get_research_context_id_nao_encontrado():
    result = await get_research_context(str(uuid.uuid4()))

    assert result.startswith("Error:")


# ── get_research_sources ─────────────────────────────────

@pytest.mark.asyncio
async def test_get_research_sources_sucesso(clean_app_state, mock_gpt_researcher):
    summary = await deep_research("topic")
    research_id = summary.split("research_id: ")[1].split("\n")[0]

    result = await get_research_sources(research_id)

    assert "source_count: 2" in result
    assert "[1] Doc 1 | https://a.com" in result
    assert "[2] Doc 2 | https://b.com" in result


@pytest.mark.asyncio
async def test_get_research_sources_uuid_invalido():
    result = await get_research_sources("../../../etc/passwd")

    assert result.startswith("Error:")
    assert "Invalid research_id" in result


@pytest.mark.asyncio
async def test_get_research_sources_id_nao_encontrado():
    result = await get_research_sources(str(uuid.uuid4()))

    assert result.startswith("Error:")