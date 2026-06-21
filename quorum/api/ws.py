"""WebSocket connection manager and stream endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import WebSocket, WebSocketDisconnect

from quorum.contracts.interfaces import EventBus

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts messages to all."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        logger.info("WS client connected. Total: %d", len(self.active))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active = [ws for ws in self.active if ws is not websocket]
        logger.info("WS client disconnected. Total: %d", len(self.active))

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for connection in self.active:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def ws_endpoint(websocket: WebSocket, event_bus: EventBus) -> None:
    """Handle a WebSocket connection, forwarding events from the bus."""
    await manager.connect(websocket)
    try:
        async for event in event_bus.subscribe():
            payload = json.dumps(event, default=str)
            await manager.broadcast(payload)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
