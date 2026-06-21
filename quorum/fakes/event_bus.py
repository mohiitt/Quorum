"""Fake EventBus that collects events in-memory for testing."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from quorum.contracts.interfaces import EventBus


class FakeEventBus(EventBus):
    """Stores published events in a list; subscribe yields from an asyncio.Queue."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def publish(self, event_dict: dict[str, Any]) -> None:
        self.events.append(event_dict)
        await self._queue.put(event_dict)

    async def subscribe(self) -> AsyncGenerator[dict[str, Any], None]:
        while True:
            event = await self._queue.get()
            yield event
