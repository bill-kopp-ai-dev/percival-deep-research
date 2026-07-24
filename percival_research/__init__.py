"""Percival Deep Research MCP Server."""

# Efeito colateral: garante que `from utils import ...` (que os submódulos
# tools/, prompts.py e resources.py usam) sempre resolva, mesmo quando o
# pacote é importado de fora do repo.
from .utils_loader import ensure_utils_module

ensure_utils_module()

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        __version__ = _pkg_version("percival-deep-research")
    except PackageNotFoundError:
        __version__ = "2.3.4"
except ImportError:
    __version__ = "1.0.0+unknown"