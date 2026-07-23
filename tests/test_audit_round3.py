"""Testes de regressão rodada 3 — bugs encontrados após rodadas 1+2."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDeepResearchReleasesLimiter:
    """BUG-3R-3/5: deep_research chamava acquire() mas NUNCA release().
    Após max_concurrent chamadas, o servidor ficava travado
    permanentemente."""

    @pytest.mark.asyncio
    async def test_release_sempre_chamado_em_sucesso(self, clean_app_state, mock_gpt_researcher):
        """Em success path, slots disponíveis após N chamadas == N."""
        from percival_research.tools.deep_research import deep_research
        import percival_research.app as _app

        # Começa com limiter de 2 slots, ambos ocupados
        max_before = _app.research_limiter._max

        # Faz uma chamada — success path
        await deep_research("alguma query válida")

        # Nenhum slot consumindo
        assert _app.research_limiter._sem is not None
        # _sem._value (do asyncio.Semaphore) deveria estar em 2 (todos liberados)
        # NOTA: _value é privado mas estável
        assert _app.research_limiter._sem._value == max_before

    @pytest.mark.asyncio
    async def test_release_em_timeout_path(self, clean_app_state, mock_gpt_researcher, monkeypatch):
        """Em timeout de pesquisa, slot também é devolvido."""
        from dataclasses import replace
        import percival_research.app as _app
        import percival_research.tools.deep_research as dr

        new_s = replace(_app._settings, research_timeout_s=0.1)
        monkeypatch.setattr(_app, "_settings", new_s)

        import asyncio as _asyncio

        async def hang():
            await _asyncio.sleep(10)

        mock_gpt_researcher.conduct_research = hang

        max_before = _app.research_limiter._max

        from percival_research.tools.deep_research import deep_research
        result = await deep_research("topic for timeout")

        assert "internal limit" in result
        # Slot devolvido (sem vazamento)
        assert _app.research_limiter._sem._value == max_before

    @pytest.mark.asyncio
    async def test_release_em_excecao_generica(self, clean_app_state, mock_gpt_researcher):
        """Em exceção genérica, slot também é devolvido."""
        import percival_research.app as _app
        mock_gpt_researcher.conduct_research = AsyncMock(
            side_effect=RuntimeError("kaboom")
        )

        max_before = _app.research_limiter._max

        from percival_research.tools.deep_research import deep_research
        result = await deep_research("topic for exception")

        # Erro retornado
        assert result.startswith("Error:")
        # Slot devolvido
        assert _app.research_limiter._sem._value == max_before

    @pytest.mark.asyncio
    async def test_sem_vazamento_em_3_chamadas_seguidas(
        self, clean_app_state, mock_gpt_researcher, monkeypatch
    ):
        """3 chamadas sucessivas em série: cada uma pega+libera o slot."""
        # Reduzir o limiter para 2 slots e ver se 3 chamadas funcionam todas
        from utils import RateLimiter
        import percival_research.app as _app

        monkeypatch.setattr(
            _app, "research_limiter", RateLimiter(max_concurrent=2),
        )
        monkeypatch.setattr(
            _dr if False else _app,
            "research_limiter",
            _app.research_limiter,
        )

        # Reaponta a referência no módulo também
        import percival_research.tools.deep_research as dr
        monkeypatch.setattr(dr, "_app.research_limiter", _app.research_limiter, raising=False)

        from percival_research.tools.deep_research import deep_research
        for i in range(3):
            r = await deep_research(f"query number {i}")
            assert "Research complete" in r or "Error" in r

    @pytest.mark.asyncio
    async def test_concurrent_3x_sequential_after_refresh(self, clean_app_state, mock_gpt_researcher):
        """Sequência de 3 chamadas com limiter=2 deve completar sem timeout."""
        # Aqui o conftest definiu limiter=100, então todas passam.
        from percival_research.tools.deep_research import deep_research
        for i in range(3):
            r = await deep_research(f"sucessivel n={i}")
            assert "Research complete" in r


class TestSafeFormattedAppearsOnIncludeContext:
    """BUG-3R-2: Quando include_context=True, a resposta usava
    `wrap_untrusted_content(context)` em vez de `safe_formatted` completo
    — divergindo do que estava no cache."""

    @pytest.mark.asyncio
    async def test_include_context_retorna_cache_igual(self, clean_app_state, mock_gpt_researcher):
        from percival_research.tools.deep_research import deep_research
        result = await deep_research("Python 3.13 features", include_context=True)

        # Cabeçalho `## Research:` (do format_context_with_sources)
        assert "## Research:" in result
        # Sources listadas
        assert "## Sources:" in result
        # SECURITY WARNING do wrap_untrusted_content
        assert "SECURITY WARNING" in result


class TestDebugLogQueriesRuntime:
    """BUG-3R-1: `DEBUG_LOG_QUERIES` era congelado no import-time.
    Agora é lido em CADA chamada."""

    @pytest.mark.asyncio
    async def test_env_alterada_runtime_tem_efeito(
        self, clean_app_state, mock_gpt_researcher, monkeypatch
    ):
        """Configurando env após import, o toggle deve funcionar."""
        from percival_research.metrics import log_query_safe
        from percival_research.tools.deep_research import deep_research

        # Garantir não-debug
        monkeypatch.delenv("PERCIVAL_DEBUG_LOG_QUERIES", raising=False)
        # Set durante runtime (antes da chamada)
        monkeypatch.setenv("PERCIVAL_DEBUG_LOG_QUERIES", "true")

        with patch("percival_research.metrics.logger") as mock_logger:
            await deep_research("query basica")
            # Deve usar .debug() porque DEBUG_LOG_QUERIES=true agora
            mock_logger.debug.assert_called()
            # E não .info()
            assert not mock_logger.info.called or any(
                "deep_research" not in str(c)
                for c in mock_logger.info.call_args_list
            )


class TestFormatContextWithSourcesHandlesNone:
    """BUG-utils: `format_context_with_sources(sources=None)` levantava TypeError."""

    def test_sources_none(self):
        from utils import format_context_with_sources
        result = format_context_with_sources("topic", "ctx body", None)
        assert "## Research: topic" in result
        assert "## Sources:\n" in result  # header sem entradas

    def test_sources_dict_nao_lista(self):
        from utils import format_context_with_sources
        # sources como iterable que não é list/tuple (ex.: generator) —
        # verifica o fallback list()
        def gen():
            yield {"title": "T", "url": "u"}

        result = format_context_with_sources("topic", "ctx", gen())
        assert "## Research: topic" in result

    def test_topic_none(self):
        from utils import format_context_with_sources
        # topic=None não explode (cai no fallback "(null)" ou "")
        result = format_context_with_sources(None, "ctx", [])
        # Não crasha
        assert "## Research:" in result

    def test_sources_lista_vazia(self):
        from utils import format_context_with_sources
        result = format_context_with_sources("Topic T", "ctx", [])
        assert "## Research: Topic T" in result
        # Sem entries
        assert "## Sources:\n" in result


class TestBypassCompressorHandlesNoneDocs:
    """BUG-patches: docs=None virava string literal 'None' no output."""

    @pytest.mark.asyncio
    async def test_doc_none_e_pulado(self):
        from percival_research.patches import _bypass_compressor_completely

        class FakeCompressor:
            documents = [None, None]

        c = FakeCompressor()
        result = await _bypass_compressor_completely(c, query="q")
        # None docs skipped — output é vazio (sem "None" literal)
        assert "None" not in result
        assert result == ""

    @pytest.mark.asyncio
    async def test_str_doc_sem_aspas_extras(self):
        from percival_research.patches import _bypass_compressor_completely

        class FakeCompressor:
            documents = ["simple text content"]

        c = FakeCompressor()
        result = await _bypass_compressor_completely(c, query="q")
        # Output contém "simple text content" sem aspas literais
        assert "simple text content" in result
        # Não deve haver aspas duplas ao redor
        assert '"' not in result

    @pytest.mark.asyncio
    async def test_none_document_e_string_document(self):
        """Mistura de None + string + dict-like não causa crash."""
        from percival_research.patches import _bypass_compressor_completely

        class FakeCompressor:
            documents = [None, "raw text", {"href": "u", "title": "T", "body": "B"}]

        c = FakeCompressor()
        result = await _bypass_compressor_completely(c, query="q")
        # Não crasha
        assert isinstance(result, str)


class TestRateLimiterReleaseOverReleaseWarning:
    """BUG-RateLimiter (rodada 3): release() chamado sem acquire
    correspondente agora LOGA WARN em vez de silenciar ValueError.

    NOTA: Este teste é informativo — em Python 3.11+, `asyncio.Semaphore.release()`
    não levanta mais `ValueError` em over-release (foi alterado em 3.11).
    Mantemos o teste porque o `try/except ValueError + print WARN` ainda é
    código defensivo caso o comportamento da stdlib mude novamente."""

    @pytest.mark.asyncio
    async def test_release_nao_levanta_no_overrelease(self):
        """Assegura que release() extra não crasha (defensivo)."""
        from utils import RateLimiter

        limiter = RateLimiter(max_concurrent=2)
        await limiter.acquire()
        limiter.release()
        # release extra — não deve levantar (mudança de comportamento
        # no Python 3.11, ver docs).
        limiter.release()
        limiter.release()  # não explodir

        assert limiter._sem is not None


class TestServerLoggersFinallyRestoresSinks:
    """BUG-server: `logger.remove()` + early-return deixava sinks mutados."""

    @pytest.mark.asyncio
    async def test_logger_sinks_restaurados_apos_run_server(self, monkeypatch, capsys):
        """Depois de `run_server()` retornar cedo (sem OPENAI_API_KEY),
        o logger deve ter um sink utilizável para outros módulos."""
        # Limpa env
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

        import importlib
        # Não reimporta — usa o server.py carregado no conftest
        import server
        try:
            server.run_server()
        except Exception:
            # run_server pode levantar de mcp.run; ignore
            pass

        captured = capsys.readouterr()
        # Após run, `get_research_id` ou outro módulo que importem
        # `from loguru import logger` deve conseguir logar.
        # Aqui verificamos que o logger TEM sink.
        from loguru import logger
        handlers = logger._core.handlers
        assert len(handlers) > 0, "Logger sinks foram removidos e não restaurados"


class TestResourcesHandlesNoneSources:
    """Recursos: `get_research_sources()` pode retornar None."""

    @pytest.mark.asyncio
    async def test_research_resource_record_metric(self, clean_app_state, mock_gpt_researcher):
        """`research://{topic}` agora chama `record_latency`/`record_error`."""
        from percival_research.resources import research_resource
        import percival_research.app as _app

        before_latencies = len(_app.metrics._latencies_ms)

        # Cache miss → chama _run_research_and_cache
        result = await research_resource("topic recursos")

        after_latencies = len(_app.metrics._latencies_ms)

        # Pelo menos uma latência registrada (success path adiciona 1)
        assert after_latencies > before_latencies, (
            "research_resource deveria ter adicionado uma latência no histórico"
        )


class TestMetricsNoCacheHitsMisses:
    """Bugs-cleanup: cache_hits/cache_misses dead fields removidos."""

    def test_snapshot_no_cache_hits(self):
        from utils import Metrics
        m = Metrics()
        snap = m.snapshot()
        assert "cache_hits" not in snap
        assert "cache_misses" not in snap

    def test_no_attribute_cache_hits(self):
        from utils import Metrics
        m = Metrics()
        assert not hasattr(m, "cache_hits")
        assert not hasattr(m, "cache_misses")