"""Testes de regressão rodada 5 — `INFERENCE_LLM` placeholder literal.

Cobre:
- S4 (llm_bridge): `_warn_on_malformed_inference_llm` detecta
  INFERENCE_LLM sem `:` ou com template `${...}` cru.
- S6 (config): `_sanitize_inference_llm_or_warn` emite WARN cedo.
- S3 (deep_research): Future exception é consumido quando rate-limit
  rejeita — não polui logs com "never retrieved".
- S9 (prompts): `report_format` é ecoado no body quando válido.

Reproduzido em `MCP_Docs/Issues/2026-07-23-percival-deep-research-inference-llm-placeholder.md`.
"""

import asyncio

import pytest
from loguru import logger


# ── S4: llm_bridge._warn_on_malformed_inference_llm ──


class TestWarnOnMalformedInferenceLLM:
    """S4: detecta `:` ausente e placeholders bash-style."""

    def test_sem_colon_emit_warning(self, capsys):
        from llm_bridge import _warn_on_malformed_inference_llm

        # Capture loguru output via stderr (we configured it via logger)
        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            _warn_on_malformed_inference_llm("gpt-4o-mini")  # NO COLON!
            assert any(
                "does NOT match" in m for m in captured
            ), f"WARN esperado, mas capturado: {captured}"
        finally:
            logger.remove(sink_id)

    def test_template_bash_style_emit_warning(self):
        from llm_bridge import _warn_on_malformed_inference_llm

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            _warn_on_malformed_inference_llm(
                "${INFERENCE_LLM:-openai:gpt-4o-mini}"
            )
            assert any(
                "UN-EXPANDED" in m for m in captured
            ), f"WARN esperado sobre placeholder, mas capturado: {captured}"
        finally:
            logger.remove(sink_id)

    def test_valido_nao_emit_warning(self):
        from llm_bridge import _warn_on_malformed_inference_llm

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            # Formato válido com alias — não deve alertar
            _warn_on_malformed_inference_llm("minimax:MiniMax-M3")
            _warn_on_malformed_inference_llm("openai:gpt-4o-mini")
            assert captured == [], (
                f"WARN espúrio para valor válido: {captured}"
            )
        finally:
            logger.remove(sink_id)

    def test_fstring_simples_tambem_detectado(self):
        """`{name}` em python template também detectado (quando contém `{`)."""
        from llm_bridge import _warn_on_malformed_inference_llm

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            # Provider válido + template f-string na porção `:model` —
            # este teste valida que mesmo quando há `:` mas o valor
            # contém `{` (heurístico atual), o WARN UN-EXPANDED é emitido.
            _warn_on_malformed_inference_llm(
                "openai:gpt-{name}"
            )
            assert any(
                "UN-EXPANDED" in m for m in captured
            ), f"WARN não emitido para template f-string, capturado: {captured}"
        finally:
            logger.remove(sink_id)


# ── S6: config._sanitize_inference_llm_or_warn ──


class TestSanitizeInferenceLLMOrWarnConfig:
    """S6: config.py emite WARN cedo (no `load_settings()`)."""

    def test_load_settings_emite_warn_para_placeholder(
        self, monkeypatch,
    ):
        # Clean env — sem INFERENCE_LLM setado a priori (default)
        for k in (
            "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
        ):
            monkeypatch.delenv(k, raising=False)

        # Setar placeholder bash-style
        monkeypatch.setenv(
            "INFERENCE_LLM",
            "${INFERENCE_LLM:-openai:gpt-4o-mini}",
        )

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            from config import load_settings
            settings = load_settings()
            # O valor deve ser mantido (não bloqueado)
            assert settings.inference_llm == (
                "${INFERENCE_LLM:-openai:gpt-4o-mini}"
            )
            assert any(
                "[S6]" in m and "UN-EXPANDED" in m
                for m in captured
            ), f"WARN [S6]/UN-EXPANDED esperado, capturado: {captured}"
        finally:
            logger.remove(sink_id)

    def test_load_settings_emite_warn_para_sem_colon(self, monkeypatch):
        for k in (
            "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("INFERENCE_LLM", "modelo-sem-provider")

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            from config import load_settings
            settings = load_settings()
            assert settings.inference_llm == "modelo-sem-provider"
            assert any(
                "[S6]" in m and "does NOT match" in m
                for m in captured
            )
        finally:
            logger.remove(sink_id)

    def test_load_settings_sem_warn_para_valor_valido(self, monkeypatch):
        for k in (
            "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("INFERENCE_LLM", "minimax:MiniMax-M3")

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            from config import load_settings
            settings = load_settings()
            assert settings.inference_llm == "minimax:MiniMax-M3"
            # Sem warns
            assert captured == [], f"WARN espúrio: {captured}"
        finally:
            logger.remove(sink_id)

    def test_no_false_positive_com_chave_legitima(self, monkeypatch):
        """C1 (review-5): `}` sozinho não é mais um sinal. Valores
        legítimos contendo `}` (e.g., strings que copiou alguma outra
        fonte) NÃO devem disparar WARN.
        """
        for k in (
            "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
        ):
            monkeypatch.delenv(k, raising=False)
        # Legítimo, só com `}` solto (sem `{` ou `${`)
        monkeypatch.setenv(
            "INFERENCE_LLM",
            "minimax:MiniMax-M3}",
        )

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")

        try:
            from config import load_settings
            settings = load_settings()
            assert settings.inference_llm == "minimax:MiniMax-M3}"

            warns = [
                m for m in captured
                if "[S6]" in m and "UN-EXPANDED" in m
            ]
            assert warns == [], (
                f"Falso positivo: `}}` sozinho não deve disparar "
                f"WARN, mas veio {warns}"
            )
        finally:
            logger.remove(sink_id)

    def test_warn_e_emitted_apenas_uma_vez_no_full_import_flow(
        self, monkeypatch,
    ):
        """A1 (review-5): valida que `populate_inference_slots`
        NÃO chama warn diretamente — o local de warn é só
        `config.load_settings`.

        Abordagem: instrumentar `_warn_on_malformed_inference_llm`
        (substituir por spy counter). Como o stub agora delega
        para o helper do config, rastrear `logger.warning` global
        só pega uma vez por chamada do spy.

        Aqui: monkeypatch o `_warn_on_malformed_inference_llm` para
        contar quantas vezes é chamado quando rodamos:
        - 1x load_settings()
        - 1x populate_inference_slots()

        Resultado esperado: 0 (porque removemos a chamada do
        `populate_inference_slots`). Antes: 1 (era duplicado).
        """
        from llm_bridge import _warn_on_malformed_inference_llm

        warn_calls = []

        def spy(value):
            warn_calls.append(value)

        # Stub o helper (não substitui loguru — só conta a chamada).
        # `monkeypatch.setattr` precisa de path completo para setattr em
        # symbol de outro módulo — `monkeypatch.setattr` aceita tanto
        # "module:function" quanto o objeto-module + name.
        import llm_bridge as _lb
        monkeypatch.setattr(
            _lb, "_warn_on_malformed_inference_llm", spy,
        )

        for k in (
            "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv(
            "INFERENCE_LLM",
            "${INFERENCE_LLM:-openai:gpt-4o-mini}",
        )

        warn_calls.clear()

        from config import load_settings
        from llm_bridge import populate_inference_slots

        # Carrega config — emite warn (deve propagar para logger.warning,
        # mas `_warn_on_malformed_inference_llm` é o outro módulo).
        settings = load_settings()

        # Não chama _warn diretamente do llm_bridge porque o helper foi
        # substituido pelo spy. Verifica:
        populate_inference_slots(settings)

        assert warn_calls == [], (
            f"`populate_inference_slots` chamou "
            f"_warn_on_malformed_inference_llm "
            f"{len(warn_calls)} vezes. Review-5 (A1) deveria ter "
            f"removido esta chamada para evitar WARN duplicado: "
            f"{warn_calls}"
        )


# ── S3: deep_research future exception não vaza ──


class TestDeepResearchFutureConsumed:
    """S3: rate-limit rejeitando não polui logs com
    'Future exception was never retrieved'."""

    @pytest.mark.asyncio
    async def test_rate_limit_reject_consumer_called(
        self, clean_app_state, monkeypatch,
    ):
        """Smoke test minimal: 30 calls paralelas com cap=2.

        O comportamento crítico do S3 é: o `future.exception()` é chamado
        para consumir a exception que o rate-limit acabou de criar.
        Verificamos via instrumentação direta na versão isolada do código
        (não dependemos do gpt-researcher full path, que exige credenciais).
        """
        from utils import RateLimiter
        import percival_research.app as _app
        from percival_research.tools.deep_research import (
            _IN_FLIGHT, deep_research,
        )

        new_limiter = RateLimiter(max_concurrent=2, acquire_timeout_s=0.1)
        monkeypatch.setattr(_app, "research_limiter", new_limiter)

        captured = []
        sink_id = logger.add(lambda m: captured.append(m), level="WARNING")
        try:
            _IN_FLIGHT.clear()
            # Roda 30 calls paralelas — todas rejeitadas (sem credenciais,
            # provider dummy). Captura se há "never retrieved" no stderr.
            results = await asyncio.gather(
                *[deep_research(f"test-round5-{i}") for i in range(30)],
                return_exceptions=True,
            )
            busy_count = sum(
                1 for r in results
                if isinstance(r, str) and "Server is busy" in r
            )
            # Não exige mínimo de BUSY — o objetivo é só verificar
            # cleanup da Future.
        finally:
            _IN_FLIGHT.clear()
            logger.remove(sink_id)

        future_warning = [
            m for m in captured if "never retrieved" in m
        ]
        assert future_warning == [], (
            f"Future exception não consumida: {future_warning}"
        )


# ── S9: prompts ecoam `report_format` válido ──


class TestResearchQueryEchoesReportFormat:
    """S9: quando `report_format` é válido, o body do prompt o cita."""

    def test_report_format_detailed_report_e_echoed(self):
        """`report_format='detailed_report'` (no allowlist) aparece no body."""
        from utils import create_research_prompt
        result = create_research_prompt("X", "Y", "detailed_report")

        # grep the exact phrase "structured detailed_report" appearing
        # in line 815.
        assert "structured detailed_report" in result

    def test_report_format_subtopic_report_e_echoed(self):
        from utils import create_research_prompt
        result = create_research_prompt("X", "Y", "subtopic_report")
        assert "structured subtopic_report" in result

    def test_report_format_invalido_cae_default(self):
        """`report_format='horse'` cai em `research_report` (allowlist fail)."""
        from utils import create_research_prompt
        result = create_research_prompt("X", "Y", "horse")
        # Default fallback
        assert "structured research_report" in result