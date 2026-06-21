"""Startup factory — creates real pipeline and injects into API dependencies.

Called from main.py lifespan. Can be skipped (deps stay as None) when running
under unit tests — tests inject fakes via set_pipeline / set_store / set_event_bus.
"""

from __future__ import annotations

import asyncio
import logging

from quorum.api.dependencies import set_event_bus, set_pipeline, set_store
from quorum.contracts.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redis health check — real round-trip, not just ping
# ---------------------------------------------------------------------------

_REDIS_TIMEOUT = 4.0  # seconds for both connect and socket I/O


async def _try_redis_url(url: str) -> "object | None":
    """
    Attempt to connect to Redis at *url*.

    Returns a RedisStore on success, None on any failure.
    Uses a wall-clock timeout so a slow/unreachable host doesn't stall startup.
    Tests with a real SET+GET to catch TLS/auth issues that ping() silently passes.
    The RedisStore returned uses the SAME socket timeout so pipeline ops also
    fail fast rather than blocking indefinitely.
    """
    from quorum.state.redis_store import RedisStore
    import redis.asyncio as aioredis

    client = None
    try:
        client = aioredis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=_REDIS_TIMEOUT,
            socket_timeout=_REDIS_TIMEOUT,
        )
        async with asyncio.timeout(_REDIS_TIMEOUT + 1):
            # Test key/value round-trip
            await client.set("quorum:health", "ok", ex=30)
            val = await client.get("quorum:health")
            if val != "ok":
                raise ValueError(f"Health check round-trip mismatch: got {val!r}")
            # Test list operations too (what the pipeline actually uses)
            await client.rpush("quorum:health_list", "ping")
            list_val = await client.lrange("quorum:health_list", 0, -1)
            await client.delete("quorum:health_list")
            if not list_val:
                raise ValueError("List operation health check failed")
        await client.aclose()
        store = RedisStore(
            url,
            socket_timeout=_REDIS_TIMEOUT,
            socket_connect_timeout=_REDIS_TIMEOUT,
        )
        return store
    except Exception as exc:
        logger.debug("Redis probe failed for %s: %s", url, exc)
        if client:
            try:
                await client.aclose()
            except Exception:
                pass
        return None


async def _connect_redis(raw_url: str):
    """
    Try raw_url, then automatically retry with TLS (rediss://) if it fails.
    Returns a (store, effective_url) tuple, or (FakeStore, None) on total failure.
    """
    from quorum.fakes import FakeStore

    # Strip trailing whitespace/newlines that env files sometimes sneak in
    url = raw_url.strip()

    store = await _try_redis_url(url)
    if store is not None:
        return store, url

    # Auto-retry with TLS if caller supplied a plain redis:// URL
    if url.startswith("redis://"):
        tls_url = "rediss://" + url[len("redis://"):]
        logger.info("Plain redis:// failed — retrying with TLS rediss://")
        store = await _try_redis_url(tls_url)
        if store is not None:
            return store, tls_url

    return FakeStore(), None


# ---------------------------------------------------------------------------
# Main initialiser
# ---------------------------------------------------------------------------


async def initialize_pipeline() -> None:
    """Wire real implementations and inject into FastAPI dependencies."""
    settings = get_settings()

    # Event bus — use Redis pub/sub when Redis is available, else in-memory
    from quorum.api.event_bus import RedisEventBus
    bus = RedisEventBus(settings.redis_url.strip())
    set_event_bus(bus)

    # Redis store — real health check, TLS auto-retry, graceful FakeStore fallback
    store, effective_url = await _connect_redis(settings.redis_url)
    set_store(store)
    if effective_url:
        print(f"[quorum] Store: Redis connected ({effective_url.split('@')[-1]})", flush=True)
    else:
        print(
            "[quorum] Store: Redis unavailable — using in-memory FakeStore "
            "(context persists for this server session only)",
            flush=True,
        )

    # Validators
    validators: list = []

    try:
        from quorum.validators.source import BrowserbaseHTTPClient, SourceValidator

        bb_client = None
        if settings.browserbase_api_key and settings.browserbase_api_key.strip("."):
            if settings.browserbase_project_id and settings.browserbase_project_id.strip("."):
                bb_client = BrowserbaseHTTPClient(
                    api_key=settings.browserbase_api_key,
                    project_id=settings.browserbase_project_id,
                )
                logger.info("Browserbase web verification enabled")
        validators.append(SourceValidator(settings=settings, browserbase_client=bb_client))
    except Exception as exc:
        logger.warning("Source validator unavailable: %s", exc)

    if settings.anthropic_api_key and settings.anthropic_api_key.strip("."):
        try:
            from quorum.validators.consistency import AnthropicLLMClient, ConsistencyValidator

            llm = AnthropicLLMClient(settings.anthropic_api_key)
            validators.append(ConsistencyValidator(llm_client=llm))
        except Exception as exc:
            logger.warning("Consistency validator unavailable: %s", exc)

        try:
            from quorum.validators.consistency import AnthropicLLMClient as RLLMClient
            from quorum.validators.reasoning import ReasoningValidator

            llm_r = RLLMClient(settings.anthropic_api_key)
            validators.append(ReasoningValidator(llm_client=llm_r))
        except Exception as exc:
            logger.warning("Reasoning validator unavailable: %s", exc)

    if not validators:
        logger.warning("No validators loaded — using FakeValidator")
        from quorum.fakes import always_accept
        validators = [always_accept("fallback")]

    # Pipeline
    from quorum.api.dependencies import get_store as _gs
    from quorum.pipeline import QuorumPipeline

    store_ref = await _gs()
    pipeline = QuorumPipeline(
        validators=validators,
        store=store_ref,
        event_bus=bus,
        settings=settings,
    )
    set_pipeline(pipeline)
    validator_names = [getattr(v, "name", type(v).__name__) for v in validators]
    print(f"[quorum] Pipeline: {len(validators)} validator(s) — {', '.join(validator_names)}", flush=True)
