"""Real asyncio-based EventBus implementations.

InMemoryEventBus — fan-out via asyncio.Queue; works for single-process deployments.
RedisEventBus   — fan-out via Redis pub/sub; supports multiple uvicorn workers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from quorum.contracts.interfaces import EventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBus):
    """Fan-out event bus using asyncio.Queue per subscriber."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

    async def publish(self, event_dict: dict[str, Any]) -> None:
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(event_dict)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    async def subscribe(self) -> AsyncGenerator[dict[str, Any], None]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        self._subscribers.append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass


class RedisEventBus(EventBus):
    """Fan-out event bus backed by Redis pub/sub.

    Supports multiple uvicorn workers — all workers share the same Redis channel.
    Falls back gracefully to InMemoryEventBus behaviour if Redis is unavailable.
    """

    CHANNEL = "quorum:events"

    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._fallback = InMemoryEventBus()

    async def publish(self, event_dict: dict[str, Any]) -> None:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(self._url, decode_responses=True)
            await client.publish(self.CHANNEL, json.dumps(event_dict, default=str))
            await client.aclose()
        except Exception as exc:
            logger.debug("RedisEventBus.publish fell back to in-memory: %s", exc)
            await self._fallback.publish(event_dict)

    async def subscribe(self) -> AsyncGenerator[dict[str, Any], None]:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(self._url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(self.CHANNEL)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            yield json.loads(message["data"])
                        except (json.JSONDecodeError, TypeError):
                            pass
            finally:
                await pubsub.unsubscribe(self.CHANNEL)
                await client.aclose()
        except Exception as exc:
            logger.debug("RedisEventBus.subscribe fell back to in-memory: %s", exc)
            async for event in self._fallback.subscribe():
                yield event
