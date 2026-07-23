"""Testes da Fase 4 — LLM bridge."""

import pytest

from config import Settings
from llm_bridge import _apply_minimax_alias, _translate_provider, normalize_llm_env


@pytest.fixture
def settings():
    return Settings(
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
        inference_api_key="",
        inference_base_url="",
        inference_llm="openai:gpt-4o-mini",
        inference_provider_alias=None,
        default_retriever="duckduckgo",
        llm_provider_aliases=("venice:", "minimax:", "openrouter:"),
        minimax_model_alias="MiniMax-M2.7",
        minimax_alias_pattern="minimax-m27",
    )


class TestTranslateProvider:
    def test_venice_para_openai(self, settings):
        assert _translate_provider("venice:llama-3.3-70b", settings) == "openai:llama-3.3-70b"

    def test_minimax_para_openai(self, settings):
        assert _translate_provider("minimax:mistral", settings) == "openai:mistral"

    def test_openrouter_para_openai(self, settings):
        assert _translate_provider("openrouter:anthropic/claude-3", settings) == "openai:anthropic/claude-3"

    def test_openai_passa_direto(self, settings):
        assert _translate_provider("openai:gpt-4o", settings) == "openai:gpt-4o"

    def test_provider_desconhecido_passa_direto(self, settings):
        assert _translate_provider("anthropic:claude-3", settings) == "anthropic:claude-3"


class TestApplyMinimaxAlias:
    def test_alias_minimax_m27_lowercase(self, settings):
        assert _apply_minimax_alias("minimax-m27-base", settings) == "MiniMax-M2.7-base"

    def test_alias_case_insensitive(self, settings):
        assert _apply_minimax_alias("MINIMAX-M27-fast", settings) == "MiniMax-M2.7-fast"

    def test_sem_alias_nao_altera(self, settings):
        assert _apply_minimax_alias("gpt-4o-mini", settings) == "gpt-4o-mini"

    def test_alias_em_substring(self, settings):
        assert _apply_minimax_alias("openai:minimax-m27-v1", settings) == "openai:MiniMax-M2.7-v1"


class TestNormalizeLLMEnv:
    def test_normaliza_fast_llm(self, monkeypatch, settings):
        monkeypatch.setenv("FAST_LLM", "venice:llama-3.3-70b")
        normalize_llm_env(settings)
        assert __import__("os").environ["FAST_LLM"] == "openai:llama-3.3-70b"

    def test_normaliza_smart_llm_com_minimax_alias(self, monkeypatch, settings):
        monkeypatch.setenv("SMART_LLM", "minimax:minimax-m27-base")
        normalize_llm_env(settings)
        # Esperado: prefixo → openai:, alias → MiniMax-M2.7
        assert __import__("os").environ["SMART_LLM"] == "openai:MiniMax-M2.7-base"

    def test_nao_faz_nada_se_env_nao_setada(self, monkeypatch, settings):
        """v2.2: como `settings.inference_llm` está setada, `populate_inference_slots`
        agora preenche todos os 4 slots. Comportamento mudou de v2.1:
        em vez de "não mexer em env vazio", popula a partir de INFERENCE_LLM."""
        monkeypatch.delenv("STRATEGIC_LLM", raising=False)
        normalize_llm_env(settings)
        assert __import__("os").environ["STRATEGIC_LLM"] == settings.inference_llm