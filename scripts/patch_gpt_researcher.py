#!/usr/bin/env python3
"""Patch de compatibilidade para `gpt-researcher >= 0.16.0` instalado em .venv.

Em v0.16.0+, o módulo `gpt_researcher/actions/query_processing.py` referencia
`Any`/`List`/`Dict` em assinaturas de função. Sob Python 3.12 (sem
`from __future__ import annotations`), o módulo falha em import com::

    NameError: name 'Any' is not defined

Em 0.16.0: as tipagens `Any`/`List` nem estão importadas.
Em 0.16.1: `from typing import Any, List, Dict` existe mas está espalhado
no meio do módulo, e `from __future__ import annotations` está ausente.

Estratégia:
- Garante que `from __future__ import annotations` apareça como a
  PRIMEIRA linha executável do módulo (após docstring de módulo).
- Idempotente: re-rodar é seguro, remove inserts duplicados anteriores.

Uso::

    uv run python scripts/patch_gpt_researcher.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def find_target() -> Path:
    """Localiza `query_processing.py` dentro do .venv ativo."""
    venv = Path(sys.executable).parent.parent
    candidate = (
        venv
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "gpt_researcher"
        / "actions"
        / "query_processing.py"
    )
    if not candidate.exists():
        print(f"ERROR: {candidate} não encontrado", file=sys.stderr)
        sys.exit(1)
    return candidate


def _module_first_stmt_idx(lines: list[str]) -> int:
    """Retorna o índice da primeira linha executável após docstring/comment.

    Docstring de módulo (uma ou múltiplas linhas) é pulada. Comentários
    e linhas em branco também. O índice retornado é onde statements
    reais (import, def, class, etc.) começam.
    """
    in_docstring = False
    doc_quote: str | None = None
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                    continue
                in_docstring = True
                doc_quote = stripped[:3]
                continue
            return i
        else:
            if doc_quote and doc_quote in ln:
                in_docstring = False
            continue
    return 0


def apply_patch(target: Path) -> bool:
    """Aplica patch idempotente. Retorna True se arquivo foi modificado."""
    src = target.read_text()
    lines = src.split("\n")

    # 0. Detectar se `from __future__ import annotations` JÁ está
    #    na posição correta antes de qualquer modificação.
    future_re = re.compile(r"^\s*from __future__ import annotations\s*$")
    first_stmt = _module_first_stmt_idx(lines)
    if (
        first_stmt < len(lines)
        and future_re.match(lines[first_stmt])
        and sum(1 for ln in lines if future_re.match(ln)) == 1
    ):
        print(f"✓ Patch já aplicado corretamente em {target}")
        return False

    # 1. Remover TODOS os `from __future__ import annotations` existentes
    #    (vão ser reinseridos na posição correta).
    lines = [ln for ln in lines if not future_re.match(ln)]
    first_stmt = _module_first_stmt_idx(lines)

    insertion = "from __future__ import annotations\n"
    new_src = "\n".join(lines[:first_stmt]) + insertion + "\n".join(lines[first_stmt:])
    target.write_text(new_src)
    print(f"✓ Patch aplicado em {target} (insert_idx={first_stmt})")
    return True


def main() -> int:
    target = find_target()
    apply_patch(target)

    try:
        import gpt_researcher.actions.query_processing  # noqa: F401

        print("✓ Módulo importa sem NameError — patch confirmado")
    except (NameError, SyntaxError) as exc:
        print(f"✗ Patch falhou: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
