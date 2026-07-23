"""Testes da Fase 2 — robustez."""

import asyncio
import time
import uuid as _uuid

import pytest

from utils import (
    DEFAULT_RESEARCH_TIMEOUT_S,
    RateLimiter,
    ResearchRegistry,
)


class TestCacheTopicTTL:
    def test_topic_expirado_e_removido(self):
        original = ResearchRegistry._CACHE_TOPIC_TTL_S
        ResearchRegistry._CACHE_TOPIC_TTL_S = 0.05
        try:
            reg = ResearchRegistry()
            reg.store("t1", "ctx", [], [])
            assert reg.has_topic("t1")
            time.sleep(0.1)
            assert not reg.has_topic("t1")
        finally:
            ResearchRegistry._CACHE_TOPIC_TTL_S = original

    def test_topic_nao_expirado_permanece(self):
        original = ResearchRegistry._CACHE_TOPIC_TTL_S
        ResearchRegistry._CACHE_TOPIC_TTL_S = 60
        try:
            reg = ResearchRegistry()
            reg.store("t1", "ctx", [], [])
            assert reg.has_topic("t1")
        finally:
            ResearchRegistry._CACHE_TOPIC_TTL_S = original

    def test_cache_misto_researchers_e_topics(self):
        """TTL de researchers e de cache são independentes."""
        orig_r = ResearchRegistry._RESEARCHER_TTL_S
        orig_c = ResearchRegistry._CACHE_TOPIC_TTL_S
        ResearchRegistry._RESEARCHER_TTL_S = 0.05
        ResearchRegistry._CACHE_TOPIC_TTL_S = 60
        try:
            reg = ResearchRegistry()
            reg.store("topic", "ctx", [], [])
            reg.add_researcher("r1", object())
            time.sleep(0.1)
            # researcher expirado, cache não
            assert not reg.get_researcher("r1")[0]
            assert reg.has_topic("topic")
        finally:
            ResearchRegistry._RESEARCHER_TTL_S = orig_r
            ResearchRegistry._CACHE_TOPIC_TTL_S = orig_c

    def test_get_cached_remove_expirado(self):
        original = ResearchRegistry._CACHE_TOPIC_TTL_S
        ResearchRegistry._CACHE_TOPIC_TTL_S = 0.05
        try:
            reg = ResearchRegistry()
            reg.store("t1", "ctx-antigo", [], [])
            time.sleep(0.1)
            # get_cached deve retornar None e remover a entrada
            assert reg.get_cached("t1") is None
            assert "t1" not in reg._store
        finally:
            ResearchRegistry._CACHE_TOPIC_TTL_S = original


class TestThreadSafety:
    """Garante que ResearchRegistry é seguro sob concorrência."""

    def test_add_researcher_thread_safe(self):
        # Com cap=200 (acima do total de ops 4*50=200), não rejeita.
        original = ResearchRegistry._MAX_RESEARCHERS
        ResearchRegistry._MAX_RESEARCHERS = 200
        try:
            reg = ResearchRegistry()
            import threading

            def worker(i):
                for j in range(50):
                    reg.add_researcher(f"r-{i}-{j}", object())

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert len(reg._researchers) == 200
        finally:
            ResearchRegistry._MAX_RESEARCHERS = original

    def test_store_topic_thread_safe(self):
        reg = ResearchRegistry()
        import threading

        def worker(i):
            for j in range(50):
                reg.store(f"t-{i}-{j}", f"ctx-{i}-{j}", [], [])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Cap de 100 é respeitado
        assert len(reg._store) <= reg._MAX_CACHED_TOPICS


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_limita_concorrencia(self):
        lim = RateLimiter(max_concurrent=2)
        active = 0
        peak = 0

        async def task():
            nonlocal active, peak
            await lim.acquire()
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.05)
            finally:
                active -= 1
                lim.release()

        await asyncio.gather(*(task() for _ in range(5)))
        assert peak == 2

    @pytest.mark.asyncio
    async def test_max_concurrent_property(self):
        lim = RateLimiter(max_concurrent=7)
        assert lim.max_concurrent == 7


class TestValidateResearchId:
    """UUID agora aceita qualquer versão RFC 4122."""

    def test_aceita_uuid_v1(self):
        from server import _validate_research_id
        v1 = str(_uuid.uuid1())
        assert _validate_research_id(v1) is True

    def test_aceita_uuid_v3(self):
        from server import _validate_research_id
        v3 = str(_uuid.uuid3(_uuid.NAMESPACE_DNS, "example.com"))
        assert _validate_research_id(v3) is True

    def test_aceita_uuid_v4(self):
        from server import _validate_research_id
        assert _validate_research_id(str(_uuid.uuid4())) is True

    def test_aceita_uuid_v5(self):
        from server import _validate_research_id
        v5 = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, "example.com"))
        assert _validate_research_id(v5) is True

    def test_rejeita_path_traversal(self):
        from server import _validate_research_id
        assert _validate_research_id("../../etc/passwd") is False

    def test_rejeita_vazio(self):
        from server import _validate_research_id
        assert _validate_research_id("") is False

    def test_rejeita_lixo(self):
        from server import _validate_research_id
        assert _validate_research_id("not-a-uuid") is False


class TestCompressorPatchGuard:
    def test_patch_aplicado_ou_avisado(self):
        """Servidor não quebra mesmo se a lib mudou."""
        import server
        assert hasattr(server, "_PATCH_OK")
        assert isinstance(server._PATCH_OK, bool)


class TestDefaultResearchTimeout:
    def test_default_90_segundos(self):
        assert DEFAULT_RESEARCH_TIMEOUT_S == 90


def test_deep_research_retorna_erro_em_timeout(monkeypatch):
    """Se a pesquisa demora mais que research_timeout_s, retorna erro claro."""
    import asyncio as _asyncio
    from dataclasses import replace
    from unittest.mock import AsyncMock, patch
    import percival_research.app as _app
    import percival_research.tools.deep_research as dr

    # Reduz o timeout para o teste não esperar 90s.
    new_settings = replace(_app._settings, research_timeout_s=0.2)
    monkeypatch.setattr(_app, "_settings", new_settings)

    async def hang_forever():
        await _asyncio.sleep(10)

    fake = AsyncMock()
    fake.conduct_research = hang_forever

    with patch("percival_research.tools.deep_research.GPTResearcher", return_value=fake):
        result = _asyncio.run(dr.deep_research("qualquer coisa"))

    assert result.startswith("Error:")
    assert "internal limit" in result
    assert "correlation_id=" in result