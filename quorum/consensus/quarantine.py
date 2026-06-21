"""Quarantine — holds claims that could not reach a clear consensus."""

from __future__ import annotations

from datetime import datetime, timezone

from quorum.contracts.interfaces import BaseStore
from quorum.contracts.models import Claim
from quorum.contracts.redis_keys import Keys


class Quarantine:
    """Manages a list of quarantined (pending-review) claims in the store.

    Each quarantined entry is stored as a dict with the claim data plus
    ``reason`` and ``quarantined_at`` metadata fields.

    All methods are async to match the BaseStore interface.
    """

    def __init__(self, store: BaseStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def quarantine(self, claim: Claim, reason: str) -> None:
        """Push *claim* onto the pending-claims list and index it by claim_id."""
        entry = {
            **claim.model_dump(mode="json"),
            "reason": reason,
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._store.list_push(Keys.PENDING_CLAIMS, entry)
        # Secondary index so callers can look up individual claims quickly.
        await self._store.set_json(
            Keys.workflow_claim(claim.workflow_id, claim.id),
            entry,
        )

    async def release(self, claim_id: str) -> None:
        """Remove the first entry with *claim_id* from the pending list."""
        items = await self._store.list_all(Keys.PENDING_CLAIMS)
        for item in items:
            if isinstance(item, dict) and item.get("id") == claim_id:
                await self._store.list_remove(Keys.PENDING_CLAIMS, item)
                return

    async def list_quarantined(self) -> list[dict]:
        """Return all currently quarantined claim entries."""
        return await self._store.list_all(Keys.PENDING_CLAIMS)

    async def is_quarantined(self, claim_id: str) -> bool:
        """Return True if *claim_id* is currently in the pending list."""
        items = await self._store.list_all(Keys.PENDING_CLAIMS)
        return any(
            isinstance(item, dict) and item.get("id") == claim_id
            for item in items
        )
