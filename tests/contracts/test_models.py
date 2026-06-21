"""Tests for shared Pydantic models."""

import pytest
from quorum.contracts.models import (
    Claim,
    ConsensusResult,
    Evidence,
    FailureMode,
    ProvenanceRecord,
    TrustScore,
    ValidatorResult,
    ValidatorName,
    Verdict,
    WorkflowContext,
)


class TestClaim:
    def test_default_id_generated(self):
        c = Claim(agent_id="a1", workflow_id="wf1", statement="test")
        assert len(c.id) == 36  # UUID

    def test_ids_are_unique(self):
        c1 = Claim(agent_id="a", workflow_id="wf", statement="x")
        c2 = Claim(agent_id="a", workflow_id="wf", statement="x")
        assert c1.id != c2.id

    def test_created_at_is_set(self):
        c = Claim(agent_id="a", workflow_id="wf", statement="x")
        assert c.created_at is not None

    def test_serialization_roundtrip(self):
        c = Claim(agent_id="a", workflow_id="wf", statement="hello")
        data = c.model_dump_json()
        restored = Claim.model_validate_json(data)
        assert restored.id == c.id
        assert restored.statement == c.statement


class TestEvidence:
    def test_quality_clamped_high(self):
        e = Evidence(source="test", snippet="s", quality=1.5)
        assert e.quality == 1.0

    def test_quality_clamped_low(self):
        e = Evidence(source="test", snippet="s", quality=-0.5)
        assert e.quality == 0.0

    def test_valid_quality(self):
        e = Evidence(source="test", snippet="s", quality=0.75)
        assert e.quality == 0.75


class TestValidatorResult:
    def test_default_failure_mode(self):
        vr = ValidatorResult(
            validator_name=ValidatorName.SOURCE,
            verdict=Verdict.ACCEPTED,
            confidence=0.9,
        )
        assert vr.failure_mode == FailureMode.NONE

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ValidatorResult(
                validator_name="x", verdict=Verdict.ACCEPTED, confidence=1.5
            )


class TestTrustScore:
    def test_acceptance_rate_zero_claims(self):
        ts = TrustScore(agent_id="a1")
        assert ts.acceptance_rate == 0.0

    def test_acceptance_rate_computed(self):
        ts = TrustScore(agent_id="a1", total_claims=10, accepted_claims=7)
        assert ts.acceptance_rate == pytest.approx(0.7)


class TestVerdictEnum:
    def test_values(self):
        assert Verdict.ACCEPTED == "accepted"
        assert Verdict.REJECTED == "rejected"
        assert Verdict.NEEDS_REVIEW == "needs_review"
