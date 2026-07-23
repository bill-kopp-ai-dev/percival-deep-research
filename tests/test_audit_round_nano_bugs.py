"""Testes de regressão para os bugs reportados pela Nano (relatório 2026-07-23).

Cobre:
- B2: `get_prompt` via FastMCP chain (AggregateProvider) não retorna None.
- B3: `INFERENCE_BASE_URL` e `INFERENCE_API_KEY` propagam para
      `OPENAI_BASE_URL`/`OPENAI_API_KEY` (que `gpt-researcher/memory/embeddings.py`
      continua lendo).
- B5: `EMBEDDING_LLM` NÃO recebe o modelo de chat — recebe default sensato
      apenas quando o provider é OpenAI-compatível.
"""

import asyncio
import os
import pytest


# ─── Helpers ────────────────────────────────────────────────────


@pytest.fixture
def fresh_env(monkeypatch):
    """Limpa todas as env vars que tocam em LLM/embedding, deixando
    o teste em um estado limpo e conhecido."""
    for var in (
        "FAST_LLM", "SMART_LLM", "STRATEGIC_LLM", "EMBEDDING_LLM",
        "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE",
        "INFERENCE_API_KEY", "INFERENCE_BASE_URL", "INFERENCE_LLM",
        "PERCIVAL_LLM_PROVIDER_ALIASES",
        "MINIMAX_MODEL_ALIAS", "MINIMAX_ALIAS_PATTERN",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ─── B3 fix: propagação INFERENCE_* → OPENAI_* ─────────────────


class TestInferencePropagatesToLegacyOpenAINamespace:
    """`gpt-researcher/memory/embeddings.py:104` ainda lê
    `OPENAI_API_KEY` e `OPENAI_BASE_URL` direto do ambiente. Sem
    o bridge em `populate_inference_slots()`, embeddings sempre
    cai no endpoint OpenAI nativo mesmo com INFERENCE_BASE_URL
    configurado."""

    def test_inference_base_url_vira_openai_base_url(self, fresh_env):
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        fresh_env.setenv("INFERENCE_API_KEY", "sk-test")
        fresh_env.setenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")

        s = load_settings()
        populate_inference_slots(s)

        # OpenAI legacy namespace populado
        assert os.environ["OPENAI_API_KEY"] == "sk-test"
        assert os.environ["OPENAI_BASE_URL"] == "https://api.venice.ai/api/v1"

    def test_legacy_openai_key_nao_foi_sobrescrito(self, fresh_env):
        """Se OPENAI_API_KEY já está setado (compat), NÃO sobrescrever."""
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        fresh_env.setenv("INFERENCE_API_KEY", "sk-new")
        fresh_env.setenv("OPENAI_API_KEY", "sk-legacy-priority")

        s = load_settings()
        populate_inference_slots(s)

        # Legacy tem precedência sobre o canônico
        assert os.environ["OPENAI_API_KEY"] == "sk-legacy-priority"

    def test_minimax_endpoint_propaga(self, fresh_env):
        """Caso de uso: o agente usa MiniMax; o MCP propaga."""
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "minimax:MiniMax-M3")
        fresh_env.setenv("INFERENCE_API_KEY", "sk-minimax")
        fresh_env.setenv("INFERENCE_BASE_URL", "https://api.minimax.io/v1")

        s = load_settings()
        populate_inference_slots(s)

        assert os.environ["OPENAI_BASE_URL"] == "https://api.minimax.io/v1"
        assert os.environ["OPENAI_API_KEY"] == "sk-minimax"


# ─── B5 fix: EMBEDDING_LLM default sensato ─────────────────────


class TestEmbeddingSlotUsesValidEmbeddingModel:
    """`EMBEDDING_LLM` não deve receber o modelo de chat, mesmo quando
    o operador só setou `INFERENCE_LLM`. Esse fix evita o cenário onde
    `gpt-4o-mini` viraria embedding model (gerando lixo)."""

    def test_embedding_nao_e_chat_model_quando_openai(self, fresh_env):
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        s = load_settings()
        populate_inference_slots(s)

        # EMBEDDING_LLM agora é text-embedding-3-small (default sensato)
        assert "embedding" in os.environ["EMBEDDING_LLM"]
        assert "gpt-4o-mini" not in os.environ["EMBEDDING_LLM"]

    def test_embedding_fica_unset_quando_provider_n_openai(self, fresh_env):
        """Para provedores não-OpenAI-compatíveis (e.g., minimax puro),
        NÃO inventar embedding. gpt-researcher deve falhar limpo
        em vez de gerar embeddings lixo."""
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "minimax:MiniMax-M3")
        s = load_settings()
        populate_inference_slots(s)

        # Sem EMBEDDING_LLM default — o operador precisa setar
        # explicitamente se quiser usar embeddings no provider não-OpenAI.
        assert "EMBEDDING_LLM" not in os.environ

    def test_embedding_override_operador_e_respeitado(self, fresh_env):
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        fresh_env.setenv("EMBEDDING_LLM", "openai:text-embedding-3-large")
        s = load_settings()
        populate_inference_slots(s)

        # Operador override não foi sobrescrito
        assert os.environ["EMBEDDING_LLM"] == "openai:text-embedding-3-large"


# ─── B2 fix: get_prompt via FastMCP chain ───────────────────────


class TestGetPromptChainFunction:
    """`mcp.get_prompt('research_query', ...)` via FastMCP client
    deve retornar o prompt renderizado (não None).

    B2: bug estava no AggregateProvider chain (`'dict' object has no
    attribute 'matches'`) — apenas `LocalProvider._get_prompt` direta
    funcionava. Reproduzimos in-process o caminho do AggregateProvider
    para garantir que o chain não quebra."""

    @pytest.mark.asyncio
    async def test_get_prompt_via_client_retorna_messages(self):
        """Smoke test do B2: client.get_prompt() não retorna None."""
        import sys
        import os
        server_py = os.path.join(
            os.path.dirname(__file__), "..", "server.py",
        )
        server_py = os.path.abspath(server_py)
        # Carrega server.py sem o `if __name__` para não disparar run_server
        with open(server_py) as f:
            src = f.read().replace(
                'if __name__ == "__main__":\n    run_server()', 'pass',
            )
        ns = {"__name__": "srv_test"}
        exec(compile(src, server_py, "exec"), ns)
        mcp = ns["mcp"]

        import fastmcp
        client = fastmcp.Client(mcp)
        async with client:
            r = await client.get_prompt(
                "research_query",
                {"topic": "Python", "goal": "latest features", "report_format": "research_report"},
            )

        # B2 detectava-se por r == None; o fix é simplesmente garantir
        # que o chain de transforms funciona e retorna GetPromptResult.
        assert r is not None, "get_prompt retornou None (B2 reproduzido)"
        assert hasattr(r, "messages")
        assert len(r.messages) >= 1
        # O conteúdo do prompt renderizado menciona o topic
        first_msg = r.messages[0]
        assert hasattr(first_msg, "content")
        assert "Python" in str(first_msg.content)


# ─── Vars propagadas para chat slots (chat-only) ────────────────


class TestChatSlotsDoNotReceiveEmbeddingOverride:
    """Garante que STRATEGIC/FAST/SMART_LLM podem receber o chat-model
    normalmente, mas EMBEDDING_LLM NÃO."""

    def test_chat_slots_recebem_inference_llm(self, fresh_env):
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        s = load_settings()
        populate_inference_slots(s)

        # 3 chat slots populados
        assert os.environ["STRATEGIC_LLM"] == "openai:gpt-4o-mini"
        assert os.environ["FAST_LLM"] == "openai:gpt-4o-mini"
        assert os.environ["SMART_LLM"] == "openai:gpt-4o-mini"

    def test_embedding_nao_recebe_chat_model_mesmo_vazio(self, fresh_env):
        """Mesmo sem override, EMBEDDING_LLM recebe default sensato,
        nunca o chat-model."""
        from config import load_settings
        from llm_bridge import populate_inference_slots

        fresh_env.setenv("INFERENCE_LLM", "openai:gpt-4o-mini")
        fresh_env.delenv("EMBEDDING_LLM", raising=False)
        s = load_settings()
        populate_inference_slots(s)

        assert os.environ["EMBEDDING_LLM"] != "openai:gpt-4o-mini"
        # É um embedding-model válido
        assert "embedding" in os.environ["EMBEDDING_LLM"]


if __name__ == "__main__":
    # Manual run: pytest tests/test_audit_round_nano_bugs.py -v
    import sys
    sys.exit(pytest.main([__file__, "-v"]))