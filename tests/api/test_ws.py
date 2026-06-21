"""Tests for WebSocket connection manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from quorum.api.ws import ConnectionManager


async def test_connect_adds_to_active():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect(ws)
    assert ws in mgr.active
    ws.accept.assert_called_once()


def test_disconnect_removes_from_active():
    mgr = ConnectionManager()
    ws = MagicMock()
    mgr.active.append(ws)
    mgr.disconnect(ws)
    assert ws not in mgr.active


async def test_broadcast_sends_to_all():
    mgr = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    mgr.active = [ws1, ws2]
    await mgr.broadcast("hello")
    ws1.send_text.assert_called_once_with("hello")
    ws2.send_text.assert_called_once_with("hello")


async def test_broadcast_removes_dead_connection():
    mgr = ConnectionManager()
    ws_alive = AsyncMock()
    ws_dead = AsyncMock()
    ws_dead.send_text.side_effect = Exception("disconnected")
    mgr.active = [ws_alive, ws_dead]
    await mgr.broadcast("test")
    assert ws_dead not in mgr.active
    assert ws_alive in mgr.active
