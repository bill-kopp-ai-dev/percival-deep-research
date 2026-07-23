#!/usr/bin/env python3
"""Patch de compatibilidade para `gpt-researcher >= 0.16.0` instalado em .venv.

Em v0.16.0, o módulo `gpt_researcher/actions/query_processing.py` referencia
`Any` e `List` sem importá-los de `typing` e sem `from __future__ import
annotations`. Sob Python 3.12 (sem annotations-postponed default), o módulo
falha em import com::

    NameError: name 'Any' is not defined

Este script aplica o patch **in-place** na cópia dentro do .venv. Idempotente.
Re-rodar é seguro; pular quando já patchado.

Uso::

    uv run python scripts/patch_gpt_researcher.py
"""
from __future__ import annotations

from pathlib import Path
import sys


def find_target() -> Path:
    """Localiza `query_processing.py` dentro do .venv ativo."""
    # sys.executable -> .../.venv/bin/python3
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


def apply_patch(target: Path) -> bool:
    """Aplica patch se ainda não estiver aplicado. Retorna True se aplicado."""
    src = target.read_text()

    if "from __future__ import annotations" in src and "from typing import Any, List" in src:
        print(f"✓ Patch já aplicado em {target}")
        return False

    # Inserir __future__ + typing import após o primeiro bloco de imports.
    needle = "from gpt_researcher.llm_provider.generic.base import ReasoningEfforts\n"
    insertion = (
        "from __future__ import annotations\n"
        "from typing import Any, List\n"
    )
    if needle in src:
        new_src = src.replace(needle, needle + insertion, 1)
    else:
        # fallback: prepend após docstring se achar
        lines = src.split("\n")
        idx = next(
            (i for i, ln in enumerate(lines) if ln.startswith("import ") or ln.startswith("from ")),
            0,
        )
        new_src = "\n".join(lines[:idx]) + insertion + "\n".join(lines[idx:])

    target.write_text(new_src)
    print(f"✓ Patch aplicado em {target}")
    return True


def main() -> int:
    target = find_target()
    apply_patch(target)
    # Smoke: tenta importar o módulo para validar
    import importlib
    try:
        import gpt_researcher.actions.query_processing  # noqa: F401
        print("✓ Módulo importa sem NameError — patch confirmado")
    except NameError as exc:
        print(f"✗ Patch falhou: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())