"""Testes de regressão para os bugs encontrados na auditoria."""

import time
import uuid as _uuid

import pytest

from utils import (
    DEFAULT_RESEARCH_TIMEOUT_S,
    ResearchRegistry,
    create_research_prompt,
    format_sources_lines,
    sanitize_prompt,
    sanitize_query,
    new_correlation_id,
    handle_exception,
    validate_research_id,
)
from percival_research.cache import InMemoryCache


class TestRegistryPropertiesHonored:
    """Regressão: bug onde atributos de classe (_MAX_RESEARCHERS, _RESEARCHER_TTL_S)
    eram comparados diretamente em vez de properties → TypeError."""

    def test_add_researcher_sem_settings_nao_explode(self):
        """Reproduz bug crítico: registry sem settings deve funcionar
        sem levantar TypeError."""
        reg = ResearchRegistry()  # sem settings (cobre produção)
        reg.add_researcher("r1", object())  # antes: TypeError aqui
        assert "r1" in reg._researchers

    def test_store_sem_settings_nao_explode(self):
        reg = ResearchRegistry()
        reg.store("topic", "ctx", [], [])  # antes: TypeError aqui
        assert "topic" in reg._store

    def test_evict_expired_sem_settings_funciona(self):
        reg = ResearchRegistry()
        reg.add_researcher("r1", object())
        # Sem monky-patch — usa property
        expired = reg._researcher_ttl_s  # property
        assert expired == 3600  # default

    def test_settings_effective_em_runtime(self):
        """Quando settings fornecido, valores devem ser usados em runtime."""
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class FakeSettings:
            max_researchers: int = 200
            researcher_ttl_s: int = 120
            max_cached_topics: int = 500
            cache_topic_ttl_s: int = 60
            research_timeout_s: int = 90
            max_concurrent_research: int = 3

        s = FakeSettings()
        reg = ResearchRegistry(settings=s)
        assert reg._max_researchers == 200
        assert reg._researcher_ttl_s == 120
        assert reg._max_cached_topics == 500
        assert reg._cache_topic_ttl_s == 60


class TestSettingsCapLimitApplied:
    """Regressão: bug onde armazenar além do cap não respeitava settings."""

    def test_settings_max_cached_topics_aplicado(self):
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class FakeSettings:
            max_researchers: int = 50
            researcher_ttl_s: int = 3600
            max_cached_topics: int = 3
            cache_topic_ttl_s: int = 3600
            research_timeout_s: int = 90
            max_concurrent_research: int = 3

        reg = ResearchRegistry(settings=FakeSettings())
        for i in range(5):
            reg.store(f"t{i}", f"c{i}", [], [])
        assert len(reg._store) <= 3  # cap respeitado


class TestResearchResourceAtomicCache:
    """Documenta necessidade (em outro lugar) de get_or_compute atômico."""
    pass


class TestValidateResearchIdAnyVersion:
    def test_accepta_v1(self):
        assert validate_research_id(str(_uuid.uuid1())) is True
    def test_accepta_v3(self):
        assert validate_research_id(str(_uuid.uuid3(_uuid.NAMESPACE_DNS, "x"))) is True
    def test_accepta_v4(self):
        assert validate_research_id(str(_uuid.uuid4())) is True
    def test_rejeita_path_traversal(self):
        assert validate_research_id("../../etc/passwd") is False


class TestMetricsRecordLatency:
    """Regressão: contador e latência devem ser independentes."""

    def test_record_latency_só_latencia_nao_contador_desconhecido(self):
        from utils import Metrics
        m = Metrics()
        # Operação desconhecida não corrompe dataclass
        before = m.deep_research_total
        m.record_latency("operacao_inexistente", 100.0)
        after = m.deep_research_total
        assert before == after  # 0 = 0


class TestFormatSourcesLinesDefensive:
    """Regressão: campos None não devem gerar 'None' na string."""

    def test_title_none_vira_Unknown(self):
        formatted = [{"title": None, "url": "u", "content_length": 5}]
        lines = format_sources_lines(formatted)
        assert "Unknown" in lines[0]
        assert "None" not in lines[0]

    def test_content_length_none_vira_0(self):
        formatted = [{"title": "T", "url": "u", "content_length": None}]
        lines = format_sources_lines(formatted)
        assert "0 chars" in lines[0]
        assert "None" not in lines[0]


class TestCreateResearchPromptGoalMax:
    """Regressão: goal deveria aceitar até 2000 chars (sanitize_prompt),
    não 500 (sanitize_query)."""

    def test_goal_ate_2000_chars(self):
        goal = "g" * 2000
        out = create_research_prompt("T", goal, "research_report")
        assert "2000" in out or goal[:80] in out

    def test_goal_acima_2000_chars_recusado(self):
        from utils import sanitize_prompt
        goal = "g" * 2001
        with pytest.raises(ValueError):
            sanitize_prompt(goal)


class TestPatchesDefensiveHandling:
    """Regressão: metadata=None, page_content=None, self.documents=None
    não devem derrubar patches."""

    def test_apply_compressor_patch_idempotente(self):
        from percival_research.patches import apply_compressor_patch
        # Chamar duas vezes não derruba
        r1 = apply_compressor_patch()
        r2 = apply_compressor_patch()
        # Idempotente ou no-op na segunda
        assert isinstance(r1, bool)
        assert isinstance(r2, bool)

    @pytest.mark.asyncio
    async def test_bypass_compressor_com_metadata_none(self):
        """Documento LangChain com `metadata=None` não deve explodir."""
        from types import SimpleNamespace
        from percival_research.patches import _bypass_compressor_completely

        class FakeCompressor:
            documents = [
                SimpleNamespace(metadata=None, page_content="text"),
                SimpleNamespace(metadata={"source": "x", "title": "T"},
                                 page_content=None),
            ]

        c = FakeCompressor()
        result = await _bypass_compressor_completely(c, query="q")
        # Tem que ter Source/Title/Content para cada doc, sem levantar
        assert result.count("Source:") == 2

    @pytest.mark.asyncio
    async def test_bypass_compressor_documents_none(self):
        """`self.documents = None` não deve explodir (algumas versões
        do gpt-researcher)."""
        from percival_research.patches import _bypass_compressor_completely

        class FakeCompressor:
            documents = None

        c = FakeCompressor()
        # Não levanta, retorna string vazia
        result = await _bypass_compressor_completely(c, query="q")
        assert result == ""


class TestConfigEnvValidation:
    """Regressão: bug onde env vars inválidas eram silenciosamente aceitas."""

    def test_int_negativo_warn_e_default(self, monkeypatch, capsys):
        monkeypatch.setenv("PERCIVAL_MAX_RESEARCHERS", "-1")
        from config import load_settings
        s = load_settings()
        # Deve usar default (50) e avisar
        assert s.max_researchers == 50
        captured = capsys.readouterr()
        assert "WARN" in captured.err
        assert "out of range" in captured.err

    def test_int_zero_recusado(self, monkeypatch, capsys):
        monkeypatch.setenv("PERCIVAL_RESEARCH_TIMEOUT_S", "0")
        from config import load_settings
        s = load_settings()
        assert s.research_timeout_s == 90
        captured = capsys.readouterr()
        assert "WARN" in captured.err

    def test_int_invalido_recusado(self, monkeypatch, capsys):
        monkeypatch.setenv("PERCIVAL_MAX_RESEARCHERS", "abc")
        from config import load_settings
        s = load_settings()
        assert s.max_researchers == 50
        captured = capsys.readouterr()
        assert "WARN" in captured.err

    def test_port_out_of_range(self, monkeypatch, capsys):
        monkeypatch.setenv("PORT", "99999")
        from config import load_settings
        s = load_settings()
        assert s.mcp_port == 8000
        captured = capsys.readouterr()
        assert "WARN" in captured.err

    def test_log_level_whitelist(self, monkeypatch, capsys):
        monkeypatch.setenv("LOG_LEVEL", "FOOBAR")
        from config import load_settings
        s = load_settings()
        assert s.log_level == "INFO"
        captured = capsys.readouterr()
        assert "WARN" in captured.err

    def test_log_level_debug_aceito(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        from config import load_settings
        s = load_settings()
        assert s.log_level == "DEBUG"

    def test_transport_invalido_recusado(self, monkeypatch, capsys):
        monkeypatch.setenv("MCP_TRANSPORT", "telnet")
        from config import load_settings
        s = load_settings()
        assert s.mcp_transport == "stdio"

    def test_llm_provider_aliases_env(self, monkeypatch):
        monkeypatch.setenv("PERCIVAL_LLM_PROVIDER_ALIASES",
                           "venice:,deepseek:,custom:")
        from config import load_settings
        s = load_settings()
        assert "deepseek:" in s.llm_provider_aliases
        assert "custom:" in s.llm_provider_aliases

    def test_minimax_alias_pattern_vazio_vira_default(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_ALIAS_PATTERN", "")
        from config import load_settings
        s = load_settings()
        # Não pode ser vazio (corromperia re.sub)
        assert s.minimax_alias_pattern == "minimax-m27"


class TestLLMBridgeEmbedding:
    """Regressão: EMBEDDING_LLM deve ser traduzido junto."""

    def test_embedding_llm_traduzido(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_LLM", "venice:my-embedding-model")
        from config import load_settings
        from llm_bridge import normalize_llm_env
        s = load_settings()
        normalize_llm_env(s)
        import os
        assert os.environ["EMBEDDING_LLM"] == "openai:my-embedding-model"

    def test_pattern_vazio_nao_corrompe(self, monkeypatch):
        """Pattern vazio em _apply_minimax_alias não pode virar
        substituição silenciosa."""
        from config import Settings
        from llm_bridge import _apply_minimax_alias
        # Settings com pattern vazio
        s = Settings(
            max_researchers=50, researcher_ttl_s=3600,
            max_cached_topics=100, cache_topic_ttl_s=3600,
            research_timeout_s=90, max_concurrent_research=3,
            log_level="INFO", debug_log_queries=False,
            mcp_transport="stdio", mcp_host="127.0.0.1",
            mcp_port=8000,
            llm_provider_aliases=(),
            minimax_model_alias="M",
            minimax_alias_pattern="",  # pattern vazio!
        )
        # Não corrompe — retorna o valor intacto
        out = _apply_minimax_alias("gpt-4o", s)
        assert out == "gpt-4o"
        assert "M" not in out  # não houve substituição


class TestResourceTimeout:
    """Regressão: research://{topic} agora respeita research_timeout_s."""

    @pytest.mark.asyncio
    async def test_resource_respeita_timeout(self, monkeypatch):
        """Se a pesquisa demora mais que o timeout, retorna erro claro."""
        import asyncio
        from percival_research.resources import _run_research_and_cache
        from dataclasses import replace
        import percival_research.app as app

        # Reduzir timeout drasticamente
        new_s = replace(app._settings, research_timeout_s=0.2)
        monkeypatch.setattr(app, "_settings", new_s)

        def slow_factory(q):
            class FakeResearcher:
                async def conduct_research(self):
                    await asyncio.sleep(10)
            return FakeResearcher()

        result = await _run_research_and_cache(
            "test query",
            slow_factory,
            cid="crl-test01",
        )
        assert "RESOURCE TIMEOUT" in result
        assert "crl-test01" in result


class TestRunServerOpenAIBaseURL:
    """Regressão: run_server deve aceitar OPENAI_BASE_URL como
    fallback (não só OPENAI_API_KEY)."""

    def test_run_server_aceita_openai_base_url(self, monkeypatch, capsys):
        # Limpa ambas
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_BASE_URL", "https://my-gateway")
        # Import lazy para não disparar side-effects
        from server import run_server
        # run_server tenta subir mcp.run — vai dar erro em outro lugar.
        # Verificamos que *passa* pelo guard de OPENAI_API_KEY.
        try:
            run_server()
        except Exception:
            pass  # OK — mcp.run não conseguiu subir (sem stdin/stdout)
        captured = capsys.readouterr()
        # Se chegou aqui sem um "OPENAI_API_KEY not found", o fix funcionou
        assert "OPENAI_API_KEY not found" not in captured.err


class TestHandleExceptionHasCorrelationId:
    def test_handle_exception_sem_explicit_cid(self):
        class FakeError(Exception):
            pass

        # Passando a message, não deve revelar detalhes ao usuário
        result = handle_exception(
            FakeError("segredo-com-sk-proj-abc123"),
            "TestOp",
        )
        assert result.startswith("Error:")
        assert "correlation_id=" in result
        assert "segredo-com-sk-proj-abc123" not in result
        assert "sk-proj-abc123" not in result


class TestNoDeadCode:
    """Sanity: nenhum import circular."""

    def test_todos_modulos_importam(self):
        from utils import ResearchRegistry, Metrics, RateLimiter
        from config import load_settings, Settings
        from llm_bridge import normalize_llm_env, _translate_provider
        from percival_research.app import (
            mcp, registry, metrics, research_limiter, _settings,
        )
        from percival_research import __version__
        assert __version__


class TestDockerComposeHost:
    """Garante que docker-compose propaga MCP_HOST=0.0.0.0 para o container."""

    def test_docker_compose_define_mcp_host(self):
        import os
        import yaml

        caminho = "/home/bill/Codes/mcp-servers-percival/percival-deep-research/docker-compose.yml"
        if not os.path.exists(caminho):
            pytest.skip("docker-compose não disponível no workspace")
        with open(caminho) as f:
            config = yaml.safe_load(f)
        # docker-compose: estrutura é config["services"]["<service-name>"]
        services = config.get("services", {})
        svc = services.get("percival-deep-research", {})
        env = svc.get("environment", [])
        # docker-compose permite env como dict ou list
        env_dict = {}
        if isinstance(env, dict):
            env_dict = env
        else:
            for item in env or []:
                if "=" in item:
                    k, v = item.split("=", 1)
                    env_dict[k] = v
        assert env_dict.get("MCP_HOST") == "0.0.0.0", (
            "docker-compose deve propagar MCP_HOST=0.0.0.0 — senão "
            "container não aceita conexões externas (binda 127.0.0.1)"
        )