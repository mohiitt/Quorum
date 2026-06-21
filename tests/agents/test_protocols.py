"""Tests for quorum.agents.protocols message models."""

import pytest

uagents = pytest.importorskip("uagents")

from quorum.agents.protocols import (  # noqa: E402
    ClaimSubmission,
    FallbackRequest,
    FallbackResponse,
    ValidationVerdict,
    quorum_protocol,
)
from uagents import Model, Protocol  # noqa: E402


# ---------------------------------------------------------------------------
# ClaimSubmission
# ---------------------------------------------------------------------------


class TestClaimSubmission:
    def test_instantiation(self):
        msg = ClaimSubmission(
            claim={"agent_id": "a1", "workflow_id": "wf-1", "statement": "It rains."},
            workflow_id="wf-1",
        )
        assert msg.workflow_id == "wf-1"
        assert isinstance(msg.claim, dict)

    def test_is_model_subclass(self):
        assert issubclass(ClaimSubmission, Model)

    def test_claim_is_dict_type(self):
        msg = ClaimSubmission(claim={"key": "value"}, workflow_id="wf-x")
        assert isinstance(msg.claim, dict)

    def test_workflow_id_is_string(self):
        msg = ClaimSubmission(claim={}, workflow_id="wf-string")
        assert isinstance(msg.workflow_id, str)


# ---------------------------------------------------------------------------
# ValidationVerdict
# ---------------------------------------------------------------------------


class TestValidationVerdict:
    def _make(self, **overrides) -> ValidationVerdict:
        defaults = dict(
            claim_id="claim-abc",
            verdict="accepted",
            score=0.92,
            rationale="Looks good",
            quarantined=False,
        )
        defaults.update(overrides)
        return ValidationVerdict(**defaults)

    def test_instantiation(self):
        msg = self._make()
        assert msg.claim_id == "claim-abc"
        assert msg.verdict == "accepted"
        assert msg.score == pytest.approx(0.92)
        assert msg.rationale == "Looks good"
        assert msg.quarantined is False

    def test_is_model_subclass(self):
        assert issubclass(ValidationVerdict, Model)

    def test_verdict_values(self):
        for v in ("accepted", "rejected", "needs_review"):
            msg = self._make(verdict=v)
            assert msg.verdict == v

    def test_quarantined_defaults_false(self):
        msg = ValidationVerdict(
            claim_id="c1", verdict="rejected", score=0.1, rationale="bad"
        )
        assert msg.quarantined is False

    def test_score_field_is_float(self):
        msg = self._make(score=0.5)
        assert isinstance(msg.score, float)

    def test_serialization_round_trip(self):
        msg = self._make(verdict="rejected", score=0.3, quarantined=True)
        data = msg.model_dump()
        restored = ValidationVerdict(**data)
        assert restored.verdict == msg.verdict
        assert restored.score == pytest.approx(msg.score)
        assert restored.quarantined == msg.quarantined


# ---------------------------------------------------------------------------
# FallbackRequest / FallbackResponse
# ---------------------------------------------------------------------------


class TestFallbackModels:
    def test_fallback_request_instantiation(self):
        req = FallbackRequest(
            original_claim_id="claim-001",
            workflow_id="wf-demo",
            failure_reason="contradicts source",
        )
        assert req.original_claim_id == "claim-001"
        assert req.workflow_id == "wf-demo"
        assert isinstance(req.failure_reason, str)

    def test_fallback_response_instantiation(self):
        resp = FallbackResponse(
            workflow_id="wf-demo",
            corrected_claim={"statement": "75% rain"},
        )
        assert resp.workflow_id == "wf-demo"
        assert isinstance(resp.corrected_claim, dict)

    def test_fallback_request_is_model(self):
        assert issubclass(FallbackRequest, Model)

    def test_fallback_response_is_model(self):
        assert issubclass(FallbackResponse, Model)


# ---------------------------------------------------------------------------
# quorum_protocol
# ---------------------------------------------------------------------------


class TestQuorumProtocol:
    def test_is_protocol_instance(self):
        assert isinstance(quorum_protocol, Protocol)

    def test_protocol_name(self):
        assert quorum_protocol.name == "QuorumValidation"
