"""Tests for ProvenanceStore using FakeStore."""

from __future__ import annotations

import pytest

from quorum.contracts.models import ConsensusResult, Verdict
from quorum.fakes.fixtures import make_claim, make_validator_result
from quorum.fakes.store import FakeStore
from quorum.state.provenance import ProvenanceStore


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def provenance(store: FakeStore) -> ProvenanceStore:
    return ProvenanceStore(store)


def _make_consensus(claim_id: str, verdict: Verdict = Verdict.ACCEPTED) -> ConsensusResult:
    vr = make_validator_result(verdict=verdict, confidence=0.9)
    return ConsensusResult(
        claim_id=claim_id,
        verdict=verdict,
        score=0.9,
        validator_results=[vr],
        rationale="Test consensus",
    )


async def test_record_stores_and_returns_provenance(provenance: ProvenanceStore) -> None:
    """record() persists a ProvenanceRecord and returns it."""
    claim = make_claim()
    consensus = _make_consensus(claim.id)

    pr = await provenance.record(claim, consensus)

    assert pr.claim_id == claim.id
    assert pr.final_verdict == Verdict.ACCEPTED
    assert pr.confidence_score == pytest.approx(0.9)
    assert pr.claim == claim
    assert pr.consensus_result == consensus


async def test_get_retrieves_stored_record(provenance: ProvenanceStore) -> None:
    """get() returns the exact record that was previously stored."""
    claim = make_claim()
    consensus = _make_consensus(claim.id)
    stored = await provenance.record(claim, consensus)

    retrieved = await provenance.get(claim.id)

    assert retrieved is not None
    assert retrieved.claim_id == stored.claim_id
    assert retrieved.final_verdict == stored.final_verdict


async def test_get_returns_none_for_unknown_claim(provenance: ProvenanceStore) -> None:
    """get() returns None when no record exists for the given claim_id."""
    result = await provenance.get("claim-does-not-exist")
    assert result is None


async def test_provenance_record_has_correct_fields(provenance: ProvenanceStore) -> None:
    """ProvenanceRecord contains the expected verdict, score, and validator names."""
    claim = make_claim()
    vr1 = make_validator_result(validator_name="source", verdict=Verdict.ACCEPTED, confidence=0.85)
    vr2 = make_validator_result(
        validator_name="consistency", verdict=Verdict.ACCEPTED, confidence=0.75
    )
    consensus = ConsensusResult(
        claim_id=claim.id,
        verdict=Verdict.ACCEPTED,
        score=0.8,
        validator_results=[vr1, vr2],
        rationale="Both validators agree",
    )

    pr = await provenance.record(claim, consensus)

    assert pr.final_verdict == Verdict.ACCEPTED
    assert pr.confidence_score == pytest.approx(0.8)
    assert set(pr.validator_names) == {"source", "consistency"}


async def test_list_for_workflow_filters_by_workflow(provenance: ProvenanceStore) -> None:
    """list_for_workflow returns only records belonging to the requested workflow."""
    claim_wf1 = make_claim(workflow_id="wf-001")
    claim_wf2 = make_claim(workflow_id="wf-002")

    await provenance.record(claim_wf1, _make_consensus(claim_wf1.id))
    await provenance.record(claim_wf2, _make_consensus(claim_wf2.id))

    wf1_records = await provenance.list_for_workflow("wf-001")
    assert len(wf1_records) == 1
    assert wf1_records[0].claim.workflow_id == "wf-001"
