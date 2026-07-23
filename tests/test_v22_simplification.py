"""Testes de regressão do release v2.2.0 — simplificação.

Cobre:
- INFERENCE_API_KEY/BASE_URL com fallback OpenAI*.
- INFERENCE_LLM popula os 4 slots automaticamente.
- Auto-detect do provider a partir de INFERENCE_BASE_URL.
- Default retriever = duckduckgo (sem precisar BRAVE_API_KEY).
- /health schema v2.2 (inference_configured em vez de openai_configured).
"""

import os
import pytest


# ════════════════════════════════════════════════════════════════
# Fase 1 — Config: INFERENCE_* com fallback OPENAI_*
# ════════════════════════════════════════════════════════════════

class TestInferenceApiKeyFallback:
    """`INFERENCE_API_KEY` substitui `OPENAI_API_KEY` (canônico), com
    fallback automático."""

    def test_inference_api_key_preferido_sobre_legacy(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_API_KEY", "k-canonic")
        monkeypatch.setenv("OPENAI_API_KEY", "k-legacy")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("INFERENCE_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_api_key == "k-canonic"

    def test_legacy_openai_api_key_como_fallback(self, monkeypatch, capsys):
        monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy")
        from config import load_settings
        s = load_settings()
        assert s.inference_api_key == "sk-legacy"
        captured = capsys.readouterr()
        assert "WARN" in captured.err
        assert "OPENAI_API_KEY" in captured.err
        assert "INFERENCE_API_KEY" in captured.err

    def test_sem_nenhum_usa_default(self, monkeypatch):
        monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_api_key == ""

    def test_inference_base_url_tambem_capa(self, monkeypatch):
        monkeypatch.delenv("INFERENCE_BASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        from config import load_settings
        s = load_settings()
        assert s.inference_base_url == "https://api.openai.com/v1"


class TestProviderAutoDetect:
    """Detecção automática do provider a partir de INFERENCE_BASE_URL."""

    def test_venice_detectada(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_provider_alias == "venice"

    def test_minimax_detectada(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://api.minimax.io/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_provider_alias == "minimax"

    def test_openrouter_detectada(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://openrouter.ai/api/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_provider_alias == "openrouter"

    def test_url_desconhecida_sem_alias(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://my-custom-llm.example.com/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        # None = sem tradução automática, mantém como 'openai:' default
        assert s.inference_provider_alias is None

    def test_base_url_vazia_sem_detect(self, monkeypatch):
        monkeypatch.delenv("INFERENCE_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.inference_provider_alias is None

    def test_alias_detectado_prepended(self, monkeypatch):
        """Se URL detecta 'venice', o alias `venice:` é adicionado nos
        `llm_provider_aliases` mesmo se o user não listar."""
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.setenv("PERCIVAL_LLM_PROVIDER_ALIASES", "minimax:,openrouter:")
        from config import load_settings
        s = load_settings()
        assert s.llm_provider_aliases[0] == "venice:"
        assert "minimax:" in s.llm_provider_aliases
        assert "openrouter:" in s.llm_provider_aliases


# ════════════════════════════════════════════════════════════════
# Fase 1 — Config: RETRIEVER default = duckduckgo
# ════════════════════════════════════════════════════════════════

class TestDefaultRetriever:
    def test_default_e_duckduckgo(self, monkeypatch):
        monkeypatch.delenv("RETRIEVER", raising=False)
        from config import load_settings
        s = load_settings()
        assert s.default_retriever == "duckduckgo"


# ════════════════════════════════════════════════════════════════
# Fase 2 — LLM Bridge: slots preenchidos a partir de INFERENCE_LLM
# ════════════════════════════════════════════════════════════════

class TestInferenceSlotsPopulated:
    def test_slots_vazios_sao_populados(self, monkeypatch):
        """Sem FAST/SMART/STRATEGIC/EMBEDDING_LLM setadas, todas vêm
        do `INFERENCE_LLM`."""
        monkeypatch.delenv("FAST_LLM", raising=False)
        monkeypatch.delenv("SMART_LLM", raising=False)
        monkeypatch.delenv("STRATEGIC_LLM", raising=False)
        monkeypatch.delenv("EMBEDDING_LLM", raising=False)
        monkeypatch.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        from config import load_settings
        from llm_bridge import apply_env_mappings
        s = load_settings()
        apply_env_mappings(s)
        # Os 3 chat slots agora têm o mesmo valor. EMBEDDING_LLM recebe
        # default sensato (B5 fix v2.2.1: NÃO é o chat model).
        assert os.environ["FAST_LLM"] == "openai:gpt-4o-mini"
        assert os.environ["SMART_LLM"] == "openai:gpt-4o-mini"
        assert os.environ["STRATEGIC_LLM"] == "openai:gpt-4o-mini"
        assert "embedding" in os.environ["EMBEDDING_LLM"]  # B5 fix

    def test_override_por_slot_e_respeitado(self, monkeypatch):
        """Se o user setou STRATEGIC_LLM, NÃO sobrescrever com INFERENCE_LLM."""
        monkeypatch.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        monkeypatch.setenv("STRATEGIC_LLM", "openai:gpt-4o")
        monkeypatch.delenv("FAST_LLM", raising=False)
        monkeypatch.delenv("SMART_LLM", raising=False)
        monkeypatch.delenv("EMBEDDING_LLM", raising=False)
        from config import load_settings
        from llm_bridge import apply_env_mappings
        s = load_settings()
        apply_env_mappings(s)
        # STRATEGIC preservado
        assert os.environ["STRATEGIC_LLM"] == "openai:gpt-4o"
        # Os outros 3 copiados do INFERENCE_LLM (chat slots)
        assert os.environ["FAST_LLM"] == "openai:gpt-4o-mini"
        assert os.environ["SMART_LLM"] == "openai:gpt-4o-mini"
        # EMBEDDING_LLM NÃO recebe o chat-model (B5 fix)
        assert "embedding" in os.environ["EMBEDDING_LLM"]  # default sensato

    def test_alias_venice_traduzido_com_autodetect(self, monkeypatch):
        """INFERENCE_LLM=venice:llama → openai:llama após apply_env_mappings."""
        monkeypatch.setenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.setenv("INFERENCE_LLM", "venice:llama-3.3-70b")
        monkeypatch.delenv("FAST_LLM", raising=False)
        monkeypatch.delenv("SMART_LLM", raising=False)
        monkeypatch.delenv("STRATEGIC_LLM", raising=False)
        monkeypatch.delenv("EMBEDDING_LLM", raising=False)
        from config import load_settings
        from llm_bridge import apply_env_mappings
        s = load_settings()
        apply_env_mappings(s)
        # venice: → openai: (alias auto-prepended de INFERENCE_BASE_URL)
        assert os.environ["INFERENCE_LLM"] == "openai:llama-3.3-70b"
        assert os.environ["FAST_LLM"] == "openai:llama-3.3-70b"


# ════════════════════════════════════════════════════════════════
# Fase 4 — Health Check: schema v2.2
# ════════════════════════════════════════════════════════════════

class TestHealthSchemaV22:
    @pytest.mark.asyncio
    async def test_schema_contem_inference_configured(self):
        """Schema v2.2 troca openai_configured → inference_configured."""
        from percival_research.app import mcp  # garante mcp carregado

        from server import health_check
        # Caso degradado (sem env, sem retriever) mas com chaves setadas
        # para forçar só o path unhealthy via retriever.
        env = {k: v for k, v in os.environ.items()
               if k not in ("RETRIEVER", "BRAVE_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(os.environ, {"INFERENCE_API_KEY": "x", "RETRIEVER": "brave"}):
                resp = await health_check(None)
                import json
                body = json.loads(resp.body)
                assert "inference_configured" in body["checks"]
                assert "openai_configured" not in body["checks"]
                assert body["checks"]["inference_configured"] is True
                assert body["checks"]["retriever_configured"] is False

    @pytest.mark.asyncio
    async def test_duckduckgo_default_nao_exige_chave(self):
        """SEM RETRIEVER setado, default é duckduckgo → healthy mesmo
        sem BRAVE_API_KEY."""
        from server import health_check
        env = {k: v for k, v in os.environ.items()
               if k not in ("RETRIEVER", "BRAVE_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(os.environ, {"INFERENCE_API_KEY": "x"}):
                resp = await health_check(None)
                assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════
# Helpers — import monkey para `patch`
# ════════════════════════════════════════════════════════════════
from unittest.mock import patch

# (Locally imported here so it's available for the @pytest.mark.asyncio
# classes above.)
