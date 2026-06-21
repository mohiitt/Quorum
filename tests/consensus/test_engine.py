"""Unit tests for ConsensusEngine."""

from __future__ import annotations

import pytest

from quorum.consensus.engine import ConsensusEngine
from quorum.contracts.config import Settings
from quorum.contracts.errors import ConsensusError
from quorum.contracts.models import Verdict
from quorum.fakes import make_validator_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def settings() -> Settings:
    return Settings(
        CONSENSUS_ACCEPT_THRESHOLD=0.70,
        CONSENSUS_REJECT_THRESHOLD=0.30,
    )


@pytest.fixture()
def engine(settings: Settings) -> ConsensusEngine:
    return ConsensusEngine(settings=settings)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConsensusEngineRun:
    def test_all_accept_returns_accepted(self, engine: ConsensusEngine) -> None:
        # score = reliability × confidence × evidence_quality(0.8)
        # 1.0 × 1.0 × 0.8 = 0.8 → above 0.70 threshold
        results = [
            make_validator_result(verdict=Verdict.ACCEPTED, confidence=1.0, reliability=1.0),
            make_validator_result(verdict=Verdict.ACCEPTED, confidence=1.0, reliability=1.0),
        ]
        cr = engine.run("claim-001", results)
        assert cr.verdict == Verdict.ACCEPTED
        assert cr.score >= 0.70

    def test_all_reject_returns_rejected(self, engine: ConsensusEngine) -> None:
        results = [
            make_validator_result(verdict=Verdict.REJECTED, confidence=0.1, reliability=0.1),
            make_validator_result(verdict=Verdict.REJECTED, confidence=0.1, reliability=0.1),
        ]
        cr = engine.run("claim-002", results)
        assert cr.verdict == Verdict.REJECTED
        assert cr.score <= 0.30

    def test_mixed_results_returns_needs_review(self, engine: ConsensusEngine) -> None:
        # score = 0.75 × 0.75 × 0.8 = 0.45 → between 0.30 and 0.70 thresholds
        results = [
            make_validator_result(verdict=Verdict.ACCEPTED, confidence=0.75, reliability=0.75),
            make_validator_result(verdict=Verdict.REJECTED, confidence=0.75, reliability=0.75),
        ]
        cr = engine.run("claim-003", results)
        assert cr.verdict == Verdict.NEEDS_REVIEW

    def test_single_validator_high_confidence_accepted(self, engine: ConsensusEngine) -> None:
        results = [
            make_validator_result(verdict=Verdict.ACCEPTED, confidence=1.0, reliability=1.0),
        ]
        cr = engine.run("claim-004", results)
        assert cr.verdict == Verdict.ACCEPTED

    def test_single_validator_low_confidence_rejected(self, engine: ConsensusEngine) -> None:
        results = [
            make_validator_result(verdict=Verdict.REJECTED, confidence=0.1, reliability=0.1),
        ]
        cr = engine.run("claim-005", results)
        assert cr.verdict == Verdict.REJECTED

    def test_empty_results_raises_consensus_error(self, engine: ConsensusEngine) -> None:
        with pytest.raises(ConsensusError, match="no validator results"):
            engine.run("claim-006", [])

    def test_rationale_is_populated(self, engine: ConsensusEngine) -> None:
        results = [make_validator_result(verdict=Verdict.ACCEPTED, confidence=0.9, reliability=0.9)]
        cr = engine.run("claim-007", results)
        assert cr.rationale, "rationale should not be empty"
        assert "ACCEPTED" in cr.rationale or "accepted" in cr.rationale.lower()

    def test_result_contains_correct_claim_id(self, engine: ConsensusEngine) -> None:
        results = [make_validator_result(verdict=Verdict.ACCEPTED, confidence=0.9, reliability=0.9)]
        cr = engine.run("my-unique-claim", results)
        assert cr.claim_id == "my-unique-claim"

    def test_result_contains_all_validator_results(self, engine: ConsensusEngine) -> None:
        results = [
            make_validator_result(verdict=Verdict.ACCEPTED),
            make_validator_result(verdict=Verdict.ACCEPTED),
        ]
        cr = engine.run("claim-008", results)
        assert len(cr.validator_results) == 2

    def test_score_is_clamped_between_0_and_1(self, engine: ConsensusEngine) -> None:
        results = [make_validator_result(confidence=1.0, reliability=1.0)]
        cr = engine.run("claim-009", results)
        assert 0.0 <= cr.score <= 1.0
