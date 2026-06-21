"""In-memory implementation of BaseStore for testing and local dev."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from quorum.contracts.interfaces import BaseStore


class FakeStore(BaseStore):
    """Thread-safe-enough in-memory store that implements BaseStore.

    Not suitable for production. Use for unit tests and local development
    without a running Redis instance.
    """

    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = defaultdict(list)

    def _encode(self, value: Any) -> str:
        return json.dumps(value, default=str)

    def _decode(self, raw: str) -> Any:
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._kv[key] = self._encode(value)

    async def get_json(self, key: str) -> Any | None:
        raw = self._kv.get(key)
        if raw is None:
            return None
        return self._decode(raw)

    async def delete(self, key: str) -> None:
        self._kv.pop(key, None)
        self._lists.pop(key, None)

    async def list_push(self, key: str, value: Any) -> None:
        self._lists[key].append(self._encode(value))

    async def list_all(self, key: str) -> list[Any]:
        return [self._decode(item) for item in self._lists.get(key, [])]

    async def list_remove(self, key: str, value: Any) -> None:
        encoded = self._encode(value)
        lst = self._lists.get(key, [])
        try:
            lst.remove(encoded)
        except ValueError:
            pass

    async def keys_matching(self, pattern: str) -> list[str]:
        import fnmatch
        return [k for k in list(self._kv.keys()) + list(self._lists.keys()) if fnmatch.fnmatch(k, pattern)]

    async def list_trim(self, key: str, start: int, stop: int) -> None:
        lst = self._lists.get(key)
        if lst is not None:
            # Redis LTRIM semantics: keep indices [start, stop] inclusive; stop=-1 means keep to end
            end = stop + 1 if stop != -1 else None
            self._lists[key] = lst[start:end]

    def reset(self) -> None:
        """Clear all stored data (useful between tests)."""
        self._kv.clear()
        self._lists.clear()
