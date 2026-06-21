"""FastAPI dependency injection container.

Real implementations are wired in Phase 9 (integration).
Tests override these via `set_*` helpers or FastAPI's `app.dependency_overrides`.
"""

from __future__ import annotations

from fastapi import HTTPException

from quorum.contracts.interfaces import BaseStore, EventBus, ValidationPipeline

_pipeline: ValidationPipeline | None = None
_store: BaseStore | None = None
_event_bus: EventBus | None = None


def set_pipeline(p: ValidationPipeline) -> None:
    global _pipeline
    _pipeline = p


def set_store(s: BaseStore) -> None:
    global _store
    _store = s


def set_event_bus(b: EventBus) -> None:
    global _event_bus
    _event_bus = b


async def get_pipeline() -> ValidationPipeline:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Validation pipeline not initialized")
    return _pipeline


async def get_store() -> BaseStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")
    return _store


async def get_event_bus() -> EventBus:
    if _event_bus is None:
        raise HTTPException(status_code=503, detail="Event bus not initialized")
    return _event_bus
