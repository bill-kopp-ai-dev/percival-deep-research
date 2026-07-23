"""Plugin layer para cache de resultados (Fase 7)."""

import threading
import time
from typing import Any, Optional, Protocol


class CacheBackend(Protocol):
    """Interface mínima para cache backend."""

    async def get(self, key: str) -> Optional[Any]:
        ...

    async def set(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...


class InMemoryCache:
    """Implementação in-process (default). Thread-safe."""

    def __init__(self):
        self._store: dict = {}
        self._lock = threading.RLock()

    async def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        with self._lock:
            expires_at = time.monotonic() + ttl_s if ttl_s else None
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


def default_cache() -> CacheBackend:
    """Retorna implementação default."""
    return InMemoryCache()


__all__ = ["CacheBackend", "InMemoryCache", "default_cache"]