"""Tools do servidor. Cada tool está em seu próprio arquivo.

Importar este pacote registra todas as tools via side-effect dos decorators
(@mcp.tool) que cada módulo executa no topo.

Atenção: este __init__ não re-exporta funções como atributos do pacote,
para preservar `percival_research.tools.deep_research` como o módulo
(submódulo) e permitir monkeypatch em testes. Callers devem importar
diretamente:

    from percival_research.tools.deep_research import deep_research
    from server import deep_research   # via re-export em server.py
"""

import importlib as _importlib

# Carregar todos os submódulos para acionar o registro via decorator.
_importlib.import_module(".deep_research", __name__)
_importlib.import_module(".get_research_context", __name__)
_importlib.import_module(".get_research_sources", __name__)
_importlib.import_module(".quick_search", __name__)
_importlib.import_module(".write_report", __name__)


def register_all(mcp) -> None:
    """Side-effect da importação basta (decorator @mcp.tool é executado)."""
    pass  # noqa: D401, D404