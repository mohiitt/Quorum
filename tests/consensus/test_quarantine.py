"""Async tests for Quarantine using FakeStore."""

from __future__ import annotations

import pytest

from quorum.consensus.quarantine import Quarantine
from quorum.fakes import FakeStore, make_claim


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture()
def quarantine(store: FakeStore) -> Quarantine:
    return Quarantine(store=store)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuarantine:
    async def test_quarantine_claim_appears_in_list(
        self, quarantine: Quarantine
    ) -> None:
        claim = make_claim(claim_id="claim-q1")
        await quarantine.quarantine(claim, reason="low consensus")
        items = await quarantine.list_quarantined()
        assert len(items) == 1
        assert items[0]["id"] == "claim-q1"

    async def test_is_quarantined_returns_true_after_quarantine(
        self, quarantine: Quarantine
    ) -> None:
        claim = make_claim(claim_id="claim-q2")
        await quarantine.quarantine(claim, reason="rejected")
        assert await quarantine.is_quarantined("claim-q2") is True

    async def test_is_quarantined_returns_false_when_not_in_list(
        self, quarantine: Quarantine
    ) -> None:
        assert await quarantine.is_quarantined("nonexistent-id") is False

    async def test_release_removes_claim_from_list(
        self, quarantine: Quarantine
    ) -> None:
        claim = make_claim(claim_id="claim-q3")
        await quarantine.quarantine(claim, reason="test")
        await quarantine.release("claim-q3")
        assert await quarantine.is_quarantined("claim-q3") is False
        assert await quarantine.list_quarantined() == []

    async def test_multiple_claims_in_quarantine(
        self, quarantine: Quarantine
    ) -> None:
        c1 = make_claim(claim_id="claim-m1")
        c2 = make_claim(claim_id="claim-m2")
        c3 = make_claim(claim_id="claim-m3")
        await quarantine.quarantine(c1, reason="r1")
        await quarantine.quarantine(c2, reason="r2")
        await quarantine.quarantine(c3, reason="r3")
        items = await quarantine.list_quarantined()
        assert len(items) == 3
        ids = {item["id"] for item in items}
        assert ids == {"claim-m1", "claim-m2", "claim-m3"}

    async def test_release_only_removes_target_claim(
        self, quarantine: Quarantine
    ) -> None:
        c1 = make_claim(claim_id="keep-a")
        c2 = make_claim(claim_id="remove-b")
        await quarantine.quarantine(c1, reason="keep")
        await quarantine.quarantine(c2, reason="remove")
        await quarantine.release("remove-b")
        items = await quarantine.list_quarantined()
        assert len(items) == 1
        assert items[0]["id"] == "keep-a"

    async def test_list_quarantined_returns_correct_structure(
        self, quarantine: Quarantine
    ) -> None:
        claim = make_claim(claim_id="struct-test", agent_id="agent-x")
        await quarantine.quarantine(claim, reason="structure check")
        items = await quarantine.list_quarantined()
        assert len(items) == 1
        entry = items[0]
        # Must have claim fields
        assert entry["id"] == "struct-test"
        assert entry["agent_id"] == "agent-x"
        # Must have quarantine metadata
        assert entry["reason"] == "structure check"
        assert "quarantined_at" in entry

    async def test_quarantine_sets_secondary_index(
        self, quarantine: Quarantine, store: FakeStore
    ) -> None:
        claim = make_claim(claim_id="idx-claim", workflow_id="wf-index")
        await quarantine.quarantine(claim, reason="index test")
        from quorum.contracts.redis_keys import Keys
        entry = await store.get_json(Keys.workflow_claim("wf-index", "idx-claim"))
        assert entry is not None
        assert entry["id"] == "idx-claim"
