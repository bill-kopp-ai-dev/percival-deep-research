"""Testes da Fase 4 — config externalizada."""

import pytest

from config import Settings, load_settings


class TestLoadSettings:
    def test_defaults(self, monkeypatch):
        for k in [
            "PERCIVAL_MAX_RESEARCHERS",
            "PERCIVAL_RESEARCHER_TTL_S",
            "PERCIVAL_MAX_CACHED_TOPICS",
            "PERCIVAL_CACHE_TOPIC_TTL_S",
            "PERCIVAL_RESEARCH_TIMEOUT_S",
            "PERCIVAL_MAX_CONCURRENT_RESEARCH",
            "MCP_TRANSPORT",
        ]:
            monkeypatch.delenv(k, raising=False)
        s = load_settings()
        assert s.max_researchers == 50
        assert s.researcher_ttl_s == 3_600
        assert s.max_cached_topics == 100
        assert s.cache_topic_ttl_s == 3_600
        assert s.research_timeout_s == 90
        assert s.max_concurrent_research == 3
        assert s.mcp_transport == "stdio"
        assert s.mcp_host == "127.0.0.1"
        assert s.mcp_port == 8000
        assert s.debug_log_queries is False

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("PERCIVAL_MAX_RESEARCHERS", "200")
        monkeypatch.setenv("PERCIVAL_RESEARCH_TIMEOUT_S", "180")
        monkeypatch.setenv("PERCIVAL_DEBUG_LOG_QUERIES", "true")
        monkeypatch.setenv("MCP_TRANSPORT", "SSE")
        s = load_settings()
        assert s.max_researchers == 200
        assert s.research_timeout_s == 180
        assert s.debug_log_queries is True
        # MCP_TRANSPORT é normalizado para lowercase
        assert s.mcp_transport == "sse"

    def test_int_invalid_vira_default(self, monkeypatch):
        monkeypatch.setenv("PERCIVAL_MAX_RESEARCHERS", "abc")
        s = load_settings()
        assert s.max_researchers == 50

    def test_host_seguro_por_default(self, monkeypatch):
        """Não regredir [M2] — default 127.0.0.1."""
        monkeypatch.delenv("MCP_HOST", raising=False)
        s = load_settings()
        assert s.mcp_host == "127.0.0.1"


class TestSettingsImmutability:
    def test_settings_e_frozen(self):
        s = Settings(
            max_researchers=50,
            researcher_ttl_s=3600,
            max_cached_topics=100,
            cache_topic_ttl_s=3600,
            research_timeout_s=90,
            max_concurrent_research=3,
            log_level="INFO",
            debug_log_queries=False,
            mcp_transport="stdio",
            mcp_host="127.0.0.1",
            mcp_port=8000,
            llm_provider_aliases=("venice:", "minimax:", "openrouter:"),
            minimax_model_alias="MiniMax-M2.7",
            minimax_alias_pattern="minimax-m27",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            s.max_researchers = 100

    def test_llm_provider_aliases_padrao(self):
        s = load_settings()
        assert "venice:" in s.llm_provider_aliases
        assert "minimax:" in s.llm_provider_aliases
        assert "openrouter:" in s.llm_provider_aliases

    def test_minimax_alias_config(self):
        s = load_settings()
        assert s.minimax_model_alias == "MiniMax-M2.7"
        assert s.minimax_alias_pattern == "minimax-m27"