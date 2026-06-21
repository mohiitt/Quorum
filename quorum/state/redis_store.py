"""Redis-backed implementation of BaseStore using redis.asyncio."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from quorum.contracts.errors import StoreError
from quorum.contracts.interfaces import BaseStore
from quorum.contracts.redis_keys import Keys


class RedisStore(BaseStore):
    """Production BaseStore backed by Redis.

    Accepts an optional pre-built client so tests can inject a FakeRedis
    instance without touching the network.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        *,
        client: aioredis.Redis | None = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ) -> None:
        self._client: aioredis.Redis = client or aioredis.from_url(
            url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # BaseStore abstract methods
    # ------------------------------------------------------------------

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        try:
            payload = json.dumps(value, default=str)
            if ttl_seconds is not None:
                await self._client.set(key, payload, ex=ttl_seconds)
            else:
                await self._client.set(key, payload)
        except Exception as exc:
            raise StoreError(f"set_json failed for key={key!r}: {exc}") from exc

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            raise StoreError(f"get_json failed for key={key!r}: {exc}") from exc

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception as exc:
            raise StoreError(f"delete failed for key={key!r}: {exc}") from exc

    async def list_push(self, key: str, value: Any) -> None:
        try:
            await self._client.rpush(key, json.dumps(value, default=str))
        except Exception as exc:
            raise StoreError(f"list_push failed for key={key!r}: {exc}") from exc

    async def list_all(self, key: str) -> list[Any]:
        try:
            items = await self._client.lrange(key, 0, -1)
            return [json.loads(item) for item in items]
        except Exception as exc:
            raise StoreError(f"list_all failed for key={key!r}: {exc}") from exc

    async def list_remove(self, key: str, value: Any) -> None:
        try:
            await self._client.lrem(key, 1, json.dumps(value, default=str))
        except Exception as exc:
            raise StoreError(f"list_remove failed for key={key!r}: {exc}") from exc

    async def list_trim(self, key: str, start: int, stop: int) -> None:
        try:
            await self._client.ltrim(key, start, stop)
        except Exception as exc:
            raise StoreError(f"list_trim failed for key={key!r}: {exc}") from exc

    async def keys_matching(self, pattern: str) -> list[str]:
        try:
            results: list[str] = []
            async for key in self._client.scan_iter(match=pattern, count=100):
                results.append(key)
            return results
        except Exception as exc:
            raise StoreError(f"keys_matching failed for pattern={pattern!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------

    async def workflow_claim_ids(self, workflow_id: str) -> list[str]:
        """Return the list of accepted claim IDs for a workflow."""
        return await self.list_all(Keys.workflow_state(workflow_id))
