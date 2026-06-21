"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from quorum.api.dependencies import get_event_bus
from quorum.api.observability import init_sentry
from quorum.api.demo import demo_router
from quorum.api.routes import router
from quorum.api.ws import ws_endpoint
from quorum.contracts.interfaces import EventBus


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    from quorum.contracts.config import get_settings
    settings = get_settings()
    init_sentry(settings.sentry_dsn)
    try:
        from quorum.api.startup import initialize_pipeline
        await initialize_pipeline()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Pipeline init skipped: %s", exc)
    yield


app = FastAPI(
    title="Quorum API",
    description="Trust and consensus layer for Fetch.ai multi-agent systems",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(demo_router)


@app.websocket("/stream")
async def websocket_stream(
    websocket: WebSocket,
    event_bus: EventBus = Depends(get_event_bus),
) -> None:
    await ws_endpoint(websocket, event_bus)
