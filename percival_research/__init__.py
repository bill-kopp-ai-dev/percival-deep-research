"""Percival Deep Research MCP Server."""

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        __version__ = _pkg_version("percival-deep-research")
    except PackageNotFoundError:
        __version__ = "1.0.0+unknown"
except ImportError:
    __version__ = "1.0.0+unknown"