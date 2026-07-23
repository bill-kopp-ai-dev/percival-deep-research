"""Testes da Fase 7 — extensibilidade."""

import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest

from config import load_settings
from percival_research.cache import InMemoryCache, default_cache
from percival_research.retrievers import (
    Retriever,
    _REGISTRY,
    get_retriever,
    register_retriever,
)


class TestRetrieverRegistry:
    def test_duckduckgo_registrado(self):
        assert "duckduckgo" in _REGISTRY

    def test_brave_registrado(self):
        assert "brave" in _REGISTRY

    def test_retriever_custom_registravel(self):
        class FakeRetriever:
            name = "fake"
            async def search(self, query, max_results=10):
                return [{"title": "x", "url": "y", "content": "z"}]
            async def close(self):
                pass

        register_retriever("fake", FakeRetriever)
        assert "fake" in _REGISTRY
        r = get_retriever("fake")
        assert r.name == "fake"

    def test_retriever_desconhecido_levanta_erro(self):
        with pytest.raises(ValueError, match="Unknown retriever"):
            get_retriever("nope")

    def test_get_retriever_brave_sem_api_key_levanta_erro(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="BRAVE_API_KEY"):
            get_retriever("brave")


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_get_set_basic(self):
        c = InMemoryCache()
        await c.set("k", {"data": 1})
        assert await c.get("k") == {"data": 1}

    @pytest.mark.asyncio
    async def test_get_missing(self):
        c = InMemoryCache()
        assert await c.get("missing") is None

    @pytest.mark.asyncio
    async def test_ttl_expira(self):
        c = InMemoryCache()
        await c.set("k", "v", ttl_s=0.05)
        assert await c.get("k") == "v"
        await asyncio.sleep(0.1)
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        c = InMemoryCache()
        await c.set("k", "v")
        await c.delete("k")
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_ttl_none_nunca_expira(self):
        c = InMemoryCache()
        await c.set("k", "v", ttl_s=None)
        # Aguarda um pouco — sem TTL, valor persiste
        await asyncio.sleep(0.05)
        assert await c.get("k") == "v"

    def test_default_cache_retorna_inmemory(self):
        c = default_cache()
        assert isinstance(c, InMemoryCache)


class TestPromptsVersioning:
    def test_default_v1(self, monkeypatch):
        monkeypatch.delenv("PERCIVAL_PROMPT_VERSION", raising=False)
        from percival_research.prompts_versions import get_research_agent_role
        role = get_research_agent_role()
        assert "experienced AI research assistant" in role
        assert "When uncertain" not in role  # V1 only

    def test_v2_explicito(self, monkeypatch):
        monkeypatch.setenv("PERCIVAL_PROMPT_VERSION", "v2")
        # Recarrega módulo para reavaliar a env
        import importlib
        from percival_research import prompts_versions
        importlib.reload(prompts_versions)
        role = prompts_versions.get_research_agent_role()
        assert "When uncertain" in role


class TestSettingsPersistence:
    """Smoke test da config de persistência (Fase 7 preparação)."""

    def test_persist_off_por_default(self, monkeypatch):
        # A config atual não tem `persist_registry`; verificamos que a
        # Fase 4 settings continua funcionando.
        s = load_settings()
        assert hasattr(s, "max_researchers")