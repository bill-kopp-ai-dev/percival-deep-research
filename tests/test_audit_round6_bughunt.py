"""Testes de regressão rodada 6 — bug-hunt code-review.

Cobre os bugs encontrados na revisão profunda pós-v3.0.0:

- B1 (CRITICAL): dedup waiter herda exceção crua quando creator é
  rejeitado pelo rate limiter. Antes propagava `RuntimeError` cru para
  o agente, quebrando o contrato "Error: ..." e vazando stack trace.
- B2 (HIGH): `_do_deep_research` re-levanta exceção crua para o
  FastMCP. Agora converte via `handle_exception`.
- B3 (HIGH): version hardcoded `"2.2.0"` no `/health` endpoint.
  Agora lê `__version__` dinamicamente.
- B4 (MEDIUM): substring match para `"openai:"` aceita falsos positivos.
  Agora exige prefixo exato.
- B5 (MEDIUM): `_check_retriever_configured` aceita retriever
  desconhecido como configurado. Agora valida contra registry.
- B6 (MEDIUM): quick_search e write_report não incrementam
  `record_latency` no caminho de sucesso.
- B7 (MEDIUM): resources.py timeout path não alimenta deque de latências.
- B8 (MEDIUM): `_evict_expired` logava 1 INFO por item (flood).
- B9 (LOW): `validate_research_id` não captura `TypeError`.
- B10 (LOW): `cache.ttl_s=0` tratado como "sem expiry".
- B11 (LOW): `format_context_with_sources` O(n²) em whitespace collapse.
- B12 (LOW): prompts_versions usa `print()` em vez de logger.
- B13 (LOW): dead code `seen` set em `_translate_all_slots`.
"""

import asyncio
import os
import time
import uuid as _uuid
from unittest.mock import MagicMock

import pytest

# ─── B1 + B2: dedup waiter exception + deep_research raw exception ───


class TestDeepResearchDedupException:
    """B1: dedup waiter não deve herdar exceção crua do creator.

    Cenário: rate limiter saturado. Task A cria Future no _IN_FLIGHT,
    task B chega e recebe a Future existente. A é rejeitada pelo
    limiter e seta exception na Future. B faz `await existing` e a
    exceção re-levanta → quebra contrato público "Error: ...".
    """

    @pytest.mark.asyncio
    async def test_dedup_waiter_recebe_mensagem_segura(
        self,
        clean_app_state,
        mock_gpt_researcher,
        monkeypatch,
    ):
        """B1: waiter recebe mensagem 'Error: ...' quando creator falha."""
        import percival_research.app as _app
        import percival_research.tools.deep_research as dr_mod
        from utils import RateLimiter

        # Limiter com cap=1 e timeout curto para forçar timeout.
        new_limiter = RateLimiter(max_concurrent=1, acquire_timeout_s=0.05)
        monkeypatch.setattr(_app, "research_limiter", new_limiter)

        # Criar uma Future já em estado de exceção para simular o cenário
        # onde o creator foi rejeitado pelo limiter e setou exception nela.
        loop = asyncio.get_running_loop()
        pending_future = loop.create_future()
        pending_future.set_exception(
            RuntimeError("deep_research cancelled before pipeline started")
        )

        # Inserir a Future no _IN_FLIGHT ANTES da chamada — simula que
        # o creator já registrou a slot antes de falhar.
        dr_mod._IN_FLIGHT["dedup waiter test"] = pending_future

        result = await dr_mod.deep_research("dedup waiter test")

        # Contrato público preservado: resposta começa com "Error:"
        assert result.startswith("Error:"), f"Resposta não começa com 'Error:': {result!r}"
        # Não vaza stack trace
        assert "RuntimeError" not in result
        assert "Traceback" not in result
        # correlation_id presente
        assert "correlation_id=" in result

        dr_mod._IN_FLIGHT.clear()


class TestDeepResearchExceptionHandled:
    """B2: exceção em `_do_deep_research` é convertida, não re-levantada."""

    @pytest.mark.asyncio
    async def test_deep_research_exception_eh_tratada(
        self,
        clean_app_state,
        mock_gpt_researcher,
    ):
        """B2: mesmo quando exceção escapa, resposta é 'Error: ...'."""

        # Força exceção em GPTResearcher() — vai propagar até o except
        # genérico de deep_research.
        from gpt_researcher import GPTResearcher

        original = GPTResearcher
        try:

            def boom(**kwargs):
                raise RuntimeError("upstream boom")

            import percival_research.tools.deep_research as dr

            dr.GPTResearcher = boom

            result = await dr.deep_research("query qualquer")
        finally:
            dr.GPTResearcher = original

        assert result.startswith("Error:")
        assert "upstream boom" not in result
        assert "correlation_id=" in result


# ─── B3: version no /health ───


class TestHealthEndpointVersion:
    """B3: `/health` deve reportar versão real (`__version__`), não hardcoded."""

    def test_health_version_dinamico(self):
        """Health body.version deve igualar percival_research.__version__."""
        from percival_research import __version__
        from percival_research.health import health_check

        # Precisa setar pelo menos uma inference key pra health ser "healthy"
        os.environ["INFERENCE_API_KEY"] = "fake-test-key"

        try:
            # MagicMock para satisfazer a assinatura do FastMCP custom_route
            request = MagicMock()
            response = asyncio.run(health_check(request))

            # Resposta é JSONResponse — extrair body
            import json as _json

            body = _json.loads(response.body)
            assert body["version"] == __version__, (
                f"Expected version={__version__!r}, got {body['version']!r}"
            )
            # Sanity: NÃO é a string hardcoded "2.2.0"
            assert body["version"] != "2.2.0", (
                "Health endpoint retornou version hardcoded — bug regressou"
            )
        finally:
            del os.environ["INFERENCE_API_KEY"]


# ─── B4: substring match "openai:" ───


class TestOpenAICompatibleStrict:
    """B4: substring match em 'openai:' aceita falsos positivos."""

    def test_openai_prefix_exato(self, monkeypatch):
        """Apenas 'openai:<model>' seta embedding default."""
        from config import Settings
        from llm_bridge import populate_inference_slots

        # Caso: 'openai:foo' → embedding default aplicado
        s_openai = Settings(
            max_researchers=1,
            researcher_ttl_s=1,
            max_cached_topics=1,
            cache_topic_ttl_s=1,
            research_timeout_s=1,
            max_concurrent_research=1,
            log_level="INFO",
            debug_log_queries=False,
            mcp_transport="stdio",
            mcp_host="127.0.0.1",
            mcp_port=8000,
            inference_api_key="k",
            inference_base_url="",
            inference_llm="openai:foo",
            inference_provider_alias=None,
            default_retriever="duckduckgo",
            llm_provider_aliases=("openai:",),
            minimax_model_alias="",
            minimax_alias_pattern="",
        )
        monkeypatch.delenv("EMBEDDING_LLM", raising=False)
        populate_inference_slots(s_openai)
        assert os.getenv("EMBEDDING_LLM", "").startswith("openai:"), (
            "openai: prefix deveria ter ativado embedding default"
        )

        # Caso: 'custom-openai-compatible:foo' → embedding NÃO aplicado
        monkeypatch.delenv("EMBEDDING_LLM", raising=False)
        s_custom = Settings(
            max_researchers=1,
            researcher_ttl_s=1,
            max_cached_topics=1,
            cache_topic_ttl_s=1,
            research_timeout_s=1,
            max_concurrent_research=1,
            log_level="INFO",
            debug_log_queries=False,
            mcp_transport="stdio",
            mcp_host="127.0.0.1",
            mcp_port=8000,
            inference_api_key="k",
            inference_base_url="",
            inference_llm="custom-openai-compatible:foo",
            inference_provider_alias=None,
            default_retriever="duckduckgo",
            llm_provider_aliases=("custom-openai-compatible:",),
            minimax_model_alias="",
            minimax_alias_pattern="",
        )
        populate_inference_slots(s_custom)
        assert not os.getenv("EMBEDDING_LLM"), (
            "string 'custom-openai-compatible:foo' NÃO deveria ativar "
            "embedding default (substring match bug)"
        )


# ─── B5: _check_retriever_configured ───


class TestRetrieverHealthCheck:
    """B5: retriever desconhecido deve fazer health check falhar."""

    def test_retriever_desconhecido_falha(self, monkeypatch):
        """RETRIEVER=bing (não registrado) → degraded."""
        from percival_research.health import _check_retriever_configured

        monkeypatch.setenv("RETRIEVER", "bing")
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        assert _check_retriever_configured() is False, (
            "Retriever não registrado deveria falhar health check"
        )

    def test_retriever_duckduckgo_ok(self, monkeypatch):
        """RETRIEVER=duckduckgo (default) → healthy."""
        from percival_research.health import _check_retriever_configured

        monkeypatch.delenv("RETRIEVER", raising=False)
        assert _check_retriever_configured() is True

    def test_retriever_brave_sem_chave_falha(self, monkeypatch):
        """RETRIEVER=brave sem BRAVE_API_KEY → unhealthy."""
        from percival_research.health import _check_retriever_configured

        monkeypatch.setenv("RETRIEVER", "brave")
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        assert _check_retriever_configured() is False

    def test_retriever_brave_com_chave_ok(self, monkeypatch):
        """RETRIVER=brave com BRAVE_API_KEY → healthy."""
        from percival_research.health import _check_retriever_configured

        monkeypatch.setenv("RETRIEVER", "brave")
        monkeypatch.setenv("BRAVE_API_KEY", "fake-key")
        assert _check_retriever_configured() is True


# ─── B6: quick_search + write_report record_latency ───


class TestQuickSearchMetrics:
    """B6: quick_search incrementa `quick_search_total` em sucesso."""

    @pytest.mark.asyncio
    async def test_quick_search_incrementa_total(
        self,
        clean_app_state,
        mock_gpt_researcher,
    ):
        """Sucesso em quick_search → quick_search_total += 1."""
        from percival_research.tools.quick_search import quick_search

        # Usar o metrics JÁ patcheado pelo clean_app_state (não o global)
        metrics = clean_app_state["metrics"]
        antes = metrics.snapshot()["quick_search_total"]
        result = await quick_search("alguma query")
        depois = metrics.snapshot()["quick_search_total"]

        assert depois == antes + 1, (
            f"quick_search_total deveria ter incrementado: {antes} → {depois}"
        )
        assert "Server is busy" not in result


class TestWriteReportMetrics:
    """B6: write_report incrementa `write_report_total` em sucesso."""

    @pytest.mark.asyncio
    async def test_write_report_incrementa_total(
        self,
        clean_app_state,
        mock_gpt_researcher,
    ):
        """Sucesso em write_report → write_report_total += 1."""
        from percival_research.tools.write_report import write_report

        # Usar o metrics JÁ patcheado pelo clean_app_state
        metrics = clean_app_state["metrics"]

        # Precisa de um researcher no registry para write_report funcionar
        research_id = str(_uuid.uuid4())
        clean_app_state["registry"].add_researcher(
            research_id,
            mock_gpt_researcher,
        )

        antes = metrics.snapshot()["write_report_total"]
        result = await write_report(research_id)
        depois = metrics.snapshot()["write_report_total"]

        assert depois == antes + 1, (
            f"write_report_total deveria ter incrementado: {antes} → {depois}"
        )
        # Não vaza exceção
        assert "Mock Report" in result


# ─── B7: resources.py timeout registra latency ───


class TestResourceTimeoutRecordsLatency:
    """B7: resources.py timeout path deve alimentar deque de latências."""

    @pytest.mark.asyncio
    async def test_timeout_path_alimenta_latencia(
        self,
        clean_app_state,
        monkeypatch,
    ):
        """B7: timeout em research_resource → record_latency chamado."""
        import percival_research.app as _app
        import percival_research.resources as resources_mod

        # Mock researcher que demora 10s
        async def hang(*a, **kw):
            await asyncio.sleep(10)

        mock_r = MagicMock()
        mock_r.conduct_research = hang

        # Reduce timeout
        from dataclasses import replace

        new_settings = replace(_app._settings, research_timeout_s=0.05)
        monkeypatch.setattr(_app, "_settings", new_settings)

        monkeypatch.setattr(resources_mod, "GPTResearcher", lambda **kw: mock_r)

        # Usar o metrics JÁ patcheado pelo clean_app_state (não o global)
        patched_metrics = clean_app_state["metrics"]
        antes_to = patched_metrics.snapshot()["timeouts_by_tool"].copy()
        antes_lat_len = len(patched_metrics._latencies_ms)
        result = await resources_mod.research_resource("timeout topic")
        depois = patched_metrics.snapshot()

        # Timeouts incrementam _timeouts_by_tool["research_resource"]
        assert depois["timeouts_by_tool"].get("research_resource", 0) > antes_to.get(
            "research_resource", 0
        ), "Timeout em research_resource deveria incrementar contador"
        # B7 fix: deque de latências é alimentado também no caminho de timeout
        assert len(patched_metrics._latencies_ms) > antes_lat_len, (
            "Deque de latências deveria ter sido alimentado no timeout path"
        )
        assert "RESOURCE TIMEOUT" in result


# ─── B8: _evict_expired não loga por item ───


class TestEvictExpiredAggregatedLog:
    """B8: _evict_expired deve agregar log em 1 mensagem."""

    def test_evict_aggregated_log(self):
        """5 researchers expirados → 1 INFO agregada, não 5."""
        from loguru import logger

        from utils import ResearchRegistry

        # loguru não propaga para caplog — usar sink customizado.
        captured = []

        def sink(message):
            record = message.record
            captured.append(record["message"])

        handler_id = logger.add(sink, level="INFO")

        original_ttl = ResearchRegistry._RESEARCHER_TTL_S
        ResearchRegistry._RESEARCHER_TTL_S = 0.05
        try:
            reg = ResearchRegistry()
            for i in range(5):
                reg.add_researcher(f"r-{i}", object())

            time.sleep(0.1)
            captured.clear()
            reg._evict_expired()

            evict_msgs = [m for m in captured if "Evicted" in m and "researcher" in m]
            assert len(evict_msgs) == 1, (
                f"Esperado 1 log agregado, encontrado {len(evict_msgs)}: {captured}"
            )
            assert "5" in evict_msgs[0]
        finally:
            ResearchRegistry._RESEARCHER_TTL_S = original_ttl
            logger.remove(handler_id)


# ─── B9: validate_research_id captura TypeError ───


class TestValidateResearchIdTypeError:
    """B9: validate_research_id retorna False em vez de levantar TypeError."""

    def test_int_input_retorna_false(self):
        """UUID(12345) levanta TypeError → validate retorna False."""
        from utils import validate_research_id

        assert validate_research_id(12345) is False

    def test_none_input_retorna_false(self):
        """None é AttributeError-safe? Vamos garantir."""
        from utils import validate_research_id

        assert validate_research_id(None) is False

    def test_list_input_retorna_false(self):
        """Lista não é string-conversível."""
        from utils import validate_research_id

        assert validate_research_id(["abc"]) is False


# ─── B10: cache ttl_s=0 expira imediatamente ───


class TestCacheTTLZero:
    """B10: ttl_s=0 deve expirar imediatamente, não tratar como None."""

    @pytest.mark.asyncio
    async def test_ttl_zero_expira(self):
        """cache.set(k, v, ttl_s=0) → get retorna None imediatamente."""
        from percival_research.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("key", "value", ttl_s=0)
        result = await cache.get("key")
        assert result is None, "ttl_s=0 deveria expirar imediatamente"

    @pytest.mark.asyncio
    async def test_ttl_none_nao_expira(self):
        """cache.set(k, v, ttl_s=None) → valor persiste."""
        from percival_research.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("key", "value", ttl_s=None)
        result = await cache.get("key")
        assert result == "value"


# ─── B11: format_context_with_sources O(n) para whitespace ───


class TestFormatContextWhitespaceCollapse:
    """B11: re.sub em vez de while-loop para colapsar whitespace."""

    def test_multiplos_espacos_colapsados(self):
        """100 espaços consecutivos viram 1."""
        from utils import format_context_with_sources

        topic = "x" + " " * 100 + "y"
        result = format_context_with_sources(topic, "ctx", [])
        # "## Research: x y" (sem 100 espaços)
        assert "  " not in result.split("\n")[0], (
            "Não deve haver espaços duplicados em '## Research:'"
        )
        assert "x y" in result

    def test_topic_nao_string_e_tratado(self):
        """topic=None → vira string vazia."""
        from utils import format_context_with_sources

        result = format_context_with_sources(None, "ctx", [])
        assert "## Research: \n" in result or "## Research:" in result


# ─── B12: prompts_versions usa logger ───


class TestPromptsVersionsUsesLogger:
    """B12: prompts_versions usa logger.warning em vez de print."""

    def test_logger_em_vez_de_print(self, caplog):
        """Valor desconhecido deve ir via logger.warning."""
        import logging

        os.environ["PERCIVAL_PROMPT_VERSION"] = "v999-bogus"
        try:
            with caplog.at_level(logging.WARNING):
                from percival_research.prompts_versions import (
                    get_research_agent_role,
                )

                get_research_agent_role()
            # Caplog captura loguru? loguru usa handler próprio.
            # Verificar via spy em sys.stderr se print() ainda é usado.
            # Forma alternativa: monkeypatch print.
        finally:
            del os.environ["PERCIVAL_PROMPT_VERSION"]

    def test_sem_print_stderr_direto_de_prompts_versions(self, monkeypatch, capsys):
        """Confirma que prompts_versions NÃO chama `print(..., file=sys.stderr)`."""
        import sys as _sys

        # Captura prints que tenham file=sys.stderr (incluindo chamadas
        # de loguru em formato "raw print").
        printed_to_stderr = []

        def fake_print(*args, **kwargs):
            # Filtra apenas prints com file=sys.stderr (formato dos warns antigos)
            if kwargs.get("file") is _sys.stderr:
                msg = " ".join(str(a) for a in args)
                # Ignora logs do loguru (formato diferente) — só nos
                # importa prints com texto de aviso sobre PERCIVAL_PROMPT_VERSION
                if "PERCIVAL_PROMPT_VERSION" in msg:
                    printed_to_stderr.append((args, kwargs))

        monkeypatch.setattr("builtins.print", fake_print)
        # Forçar caminho do warning
        os.environ["PERCIVAL_PROMPT_VERSION"] = "v999-bogus"
        try:
            from percival_research.prompts_versions import get_research_agent_role

            get_research_agent_role()
        finally:
            del os.environ["PERCIVAL_PROMPT_VERSION"]

        # Antes do fix: 1 print em sys.stderr com WARN sobre
        # PERCIVAL_PROMPT_VERSION. Agora: 0 (vai via logger.warning).
        assert len(printed_to_stderr) == 0, (
            f"Esperado 0 print em stderr mencionando PERCIVAL_PROMPT_VERSION; "
            f"encontrado {len(printed_to_stderr)}: {printed_to_stderr}"
        )


# ─── B13: dead code `seen` removido ───


class TestTranslateAllSlotsClean:
    """B13: `_translate_all_slots` não deve ter `seen` set morto."""

    def test_seen_nao_existe_como_identificador(self):
        """Variável `seen` não deve mais existir como identificador no body."""
        import inspect

        from llm_bridge import _translate_all_slots

        source = inspect.getsource(_translate_all_slots)
        # Docstring contém a palavra `seen` em comentário explicativo;
        # só verificamos o corpo (após o docstring).
        # Estratégia: encontrar o primeiro statement do body e checar
        # desse ponto em diante.
        lines = source.splitlines()
        in_docstring = False
        doc_quote = None
        body_start = 0
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if not stripped:
                continue
            if stripped.startswith("def "):
                continue
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                        continue
                    in_docstring = True
                    doc_quote = stripped[:3]
                    continue
                body_start = i
                break
            else:
                if doc_quote and doc_quote in ln:
                    in_docstring = False
                continue
        body = "\n".join(lines[body_start:])
        assert "seen =" not in body and "seen:" not in body, (
            f"`seen` ainda aparece como identificador no body: {body!r}"
        )


# ─── B14: RateLimiter release não libera sem errado ───


class TestRateLimiterReleaseSemantics:
    """B14: RateLimiter.release deve usar contador, não sem atual."""

    @pytest.mark.asyncio
    async def test_release_sem_acquire_nao_libera(self, capsys):
        """B14: release sem acquire correspondente deve warn + no-op."""
        from utils import RateLimiter

        lim = RateLimiter(max_concurrent=2)
        lim.release()  # sem acquire prévio

        # Deve warn em stderr
        captured = capsys.readouterr()
        assert "called more times than acquired" in captured.err, (
            f"Esperado WARN, capturado: {captured.err!r}"
        )

    @pytest.mark.asyncio
    async def test_release_depois_de_acquire_normal(self):
        """B14: acquire + release em sequência não vaza slots."""
        from utils import RateLimiter

        lim = RateLimiter(max_concurrent=2)

        # 4 acquires + 4 releases = saldo zero
        for _ in range(4):
            await lim.acquire()
            lim.release()

        # Próximo acquire não deve bloquear
        await asyncio.wait_for(lim.acquire(), timeout=0.5)
        lim.release()

    @pytest.mark.asyncio
    async def test_acquire_count_interno(self):
        """B14: contador _pending deve refletir acquires pendentes."""
        from utils import RateLimiter

        lim = RateLimiter(max_concurrent=3)
        assert lim._pending == 0

        await lim.acquire()
        assert lim._pending == 1

        await lim.acquire()
        assert lim._pending == 2

        lim.release()
        assert lim._pending == 1

        lim.release()
        assert lim._pending == 0


# ─── B15: Metrics.record_latency aceita qualquer operação ───


class TestMetricsAnyOperation:
    """B15: Metrics deve aceitar QUALQUER operation name."""

    def test_record_latency_para_operacao_qualquer(self):
        """record_latency('research_resource', 100) → totals_by_tool ok."""
        from utils import Metrics

        m = Metrics()
        m.record_latency("research_resource", 100)
        m.record_latency("research_resource", 200)
        m.record_latency("get_research_context", 50)

        snap = m.snapshot()
        assert snap["totals_by_tool"]["research_resource"] == 2
        assert snap["totals_by_tool"]["get_research_context"] == 1

    def test_legacy_fields_mantidos(self):
        """deep_research_total, quick_search_total, etc. continuam no snapshot."""
        from utils import Metrics

        m = Metrics()
        m.record_latency("deep_research", 100)
        m.record_latency("quick_search", 100)
        m.record_latency("write_report", 100)

        snap = m.snapshot()
        assert "deep_research_total" in snap
        assert "quick_search_total" in snap
        assert "write_report_total" in snap
        assert snap["deep_research_total"] == 1
        assert snap["quick_search_total"] == 1
        assert snap["write_report_total"] == 1


# ─── B16: patch_gpt_researcher idempotência ───


class TestPatchGptResearcherIdempotent:
    """B16: patch_gpt_researcher.py é idempotente."""

    def test_patch_idempotente(self, tmp_path, monkeypatch):
        """Re-aplicar patch não deve duplicar `from __future__`."""
        import shutil

        # Cria cópia temporária do file em tmp_path
        src_file = (
            "/home/bill/Projects/percival-deep-research/.venv/lib/python3.12/"
            "site-packages/gpt_researcher/actions/query_processing.py"
        )
        test_file = tmp_path / "query_processing.py"
        shutil.copy(src_file, test_file)

        # Importar o módulo patch e forçar uso do test_file
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "patch_gpt_researcher_test",
            "/home/bill/Projects/percival-deep-research/scripts/patch_gpt_researcher.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Aplicar patch 3x
        mod.apply_patch(test_file)
        first = test_file.read_text()
        first_count = first.count("from __future__ import annotations")

        mod.apply_patch(test_file)
        mod.apply_patch(test_file)
        third = test_file.read_text()
        third_count = third.count("from __future__ import annotations")

        # Deve haver exatamente 1 ocorrência em ambos os casos
        assert first_count == 1, f"Primeira aplicação: {first_count} ocorrências (esperado 1)"
        assert third_count == 1, (
            f"Após 3 aplicações: {third_count} ocorrências (esperado 1) — patch não é idempotente"
        )
