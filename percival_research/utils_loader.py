"""Shim que garante `utils` module-top-level está no sys.path
mesmo quando o pacote `percival_research` é importado de fora do repo
(cli tools, pytest collect, deploy).

Estratégia:
1. Adiciona `<package_root>/` (onde `utils.py` reside) ao `sys.path`
   se ainda não estiver.
2. Mantém o módulo-level `utils` importável via `import utils`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_utils_module() -> bool:
    """Garante que `import utils` (top-level) resolve para `<root>/utils.py`.

    O package `percival-deep-research` mantém `utils.py` na raiz por
    compat com o server entrypoint (`server.py` rodando diretamente).
    Esse shim garante a mesma UX quando o código importa via
    `percival_research.*`.

    Returns:
        True se `sys.path` foi modificada (útil em testes que querem
        verificar se o side-effect rolou).
    """
    package_root = Path(__file__).resolve().parent.parent
    candidate = package_root / "utils.py"
    if candidate.exists():
        package_root_str = str(package_root)
        if package_root_str not in sys.path:
            sys.path.insert(0, package_root_str)
            return True
    return False