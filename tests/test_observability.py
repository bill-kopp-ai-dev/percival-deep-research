"""Testes da Fase 3 — observabilidade."""

import json
import os
from unittest.mock import patch

import pytest

from server import Metrics


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_quando_tudo_configurado(self):
        from server import health_check
        with patch.dict(os.environ, {"OPENAI_API_KEY": "x", "RETRIEVER": "brave"}):
            resp = await health_check(None)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_degraded_sem_openai_key(self):
        from server import health_check
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(os.environ, {"RETRIEVER": "brave"}):
                resp = await health_check(None)
                assert resp.status_code == 503
                assert json.loads(resp.body)["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_degraded_sem_retriever(self):
        from server import health_check
        env = {k: v for k, v in os.environ.items() if k not in ("RETRIEVER", "BRAVE_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}):
                resp = await health_check(None)
                assert resp.status_code == 503
                body = json.loads(resp.body)
                assert body["checks"]["retriever_configured"] is False


class TestLogSafeQuery:
    def test_preview_truncado(self):
        # _log_query_safe foi movido para percival_research.metrics
        from percival_research.metrics import log_query_safe
        long_q = "a" * 1000
        with patch("percival_research.metrics.logger") as mock_logger:
            log_query_safe("Deep research", long_q, "crl-test")
            logged = mock_logger.info.call_args[0][0]
            assert "crl-test" in logged
            assert "a" * 81 not in logged  # truncado
            assert "a" * 80 in logged  # preview presente

    def test_newlines_removidos(self):
        from percival_research.metrics import log_query_safe
        with patch("percival_research.metrics.logger") as mock_logger:
            log_query_safe("Deep research", "linha1\nlinha2", "crl-x")
            logged = mock_logger.info.call_args[0][0]
            assert "\n" not in logged.split("preview=")[1]

    def test_debug_mode_loga_query_completa(self, monkeypatch):
        """Audit rodada 3 BUG-3R-1: agora a env é lida em runtime
        (não no import-time), então `monkeypatch.setenv` ativa
        imediatamente — sem precisar de `importlib.reload`."""
        monkeypatch.setenv("PERCIVAL_DEBUG_LOG_QUERIES", "true")
        from percival_research.metrics import log_query_safe
        with patch("percival_research.metrics.logger") as mock_logger:
            log_query_safe("Deep research", "secret query", "crl-d")
            mock_logger.debug.assert_called_once()
            logged = mock_logger.debug.call_args[0][0]
            assert "secret query" in logged
        monkeypatch.delenv("PERCIVAL_DEBUG_LOG_QUERIES", raising=False)


class TestMetrics:
    def test_record_latency_basic(self):
        m = Metrics()
        m.record_latency("deep_research", 100.0)
        snap = m.snapshot()
        assert snap["deep_research_total"] == 1

    def test_p50_calculado(self):
        m = Metrics()
        for v in [10, 20, 30, 40, 50]:
            m.record_latency("deep_research", v)
        snap = m.snapshot()
        assert snap["p50_latency_ms"] == 30

    def test_snapshot_thread_safe(self):
        import threading
        m = Metrics()

        def worker():
            for _ in range(100):
                m.record_latency("deep_research", 10.0)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        snap = m.snapshot()
        assert snap["deep_research_total"] == 400

    def test_record_timeout_generico_por_tool(self):
        m = Metrics()
        m.record_timeout("quick_search")
        m.record_timeout("quick_search")
        m.record_timeout("deep_research")
        snap = m.snapshot()
        assert snap["timeouts_by_tool"]["quick_search"] == 2
        assert snap["timeouts_by_tool"]["deep_research"] == 1
        assert snap["deep_research_timeout"] == 1

    def test_record_error_generico_por_tool(self):
        m = Metrics()
        m.record_error("write_report")
        snap = m.snapshot()
        assert snap["errors_by_tool"]["write_report"] == 1
        assert snap["deep_research_errors"] == 0


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_retorna_json(self):
        from server import metrics_endpoint, metrics
        metrics.record_latency("deep_research", 42.0)
        resp = await metrics_endpoint(None)
        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert "deep_research_total" in body
        assert "p50_latency_ms" in body