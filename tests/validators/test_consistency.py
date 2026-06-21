"""Tests for the ConsistencyValidator (Phase 2).

All tests use FakeLLMClient — no real Anthropic calls are made.
pytest-asyncio is configured with asyncio_mode = "auto" in pyproject.toml.
"""

from __future__ import annotations

import json

import pytest

from quorum.contracts.interfaces import BaseValidator
from quorum.contracts.models import FailureMode, Verdict
from quorum.fakes import FakeLLMClient, make_claim, make_workflow_context
from quorum.validators.consistency import ConsistencyValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _llm_response(
    *,
    contradicts: bool,
    confidence: float,
    rationale: str = "Test rationale",
    contradicted_claim_id: str | None = None,
) -> str:
    return json.dumps(
        {
            "contradicts": contradicts,
            "confidence": confidence,
            "rationale": rationale,
            "contradicted_claim_id": contradicted_claim_id,
        }
    )


def _make_validator(response: str) -> tuple[ConsistencyValidator, FakeLLMClient]:
    llm = FakeLLMClient(response=response)
    validator = ConsistencyValidator(llm_client=llm)
    return validator, llm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_no_prior_claims_returns_accepted_with_moderate_confidence():
    """With no accepted claims, the validator accepts with confidence 0.9 (no LLM call)."""
    validator, llm = _make_validator(_llm_response(contradicts=False, confidence=0.9))
    claim = make_claim(statement="Rain is expected tomorrow.")
    context = make_workflow_context(accepted_claims=[])

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.ACCEPTED
    assert abs(result.confidence - 0.9) < 1e-9
    assert result.failure_mode == FailureMode.NONE
    # LLM should NOT be called when there are no prior claims
    assert len(llm.calls) == 0


async def test_llm_says_no_contradiction_returns_accepted():
    """LLM reports no contradiction → ACCEPTED with the LLM's confidence."""
    prior = make_claim(statement="The sky is blue.")
    validator, llm = _make_validator(
        _llm_response(contradicts=False, confidence=0.95, rationale="Claims are consistent.")
    )
    claim = make_claim(statement="The sky is clear today.")
    context = make_workflow_context(accepted_claims=[prior])

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.ACCEPTED
    assert result.confidence == 0.95
    assert result.failure_mode == FailureMode.NONE
    assert "consistent" in result.rationale


async def test_llm_says_contradiction_returns_rejected():
    """LLM reports contradiction → REJECTED with CONTRADICTS_WORKFLOW failure mode."""
    prior = make_claim(statement="The market will go up.", claim_id="claim-abc")
    validator, llm = _make_validator(
        _llm_response(
            contradicts=True,
            confidence=0.88,
            rationale="New claim directly contradicts the prior forecast.",
            contradicted_claim_id="claim-abc",
        )
    )
    claim = make_claim(statement="The market will crash tomorrow.")
    context = make_workflow_context(accepted_claims=[prior])

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.REJECTED
    assert result.failure_mode == FailureMode.CONTRADICTS_WORKFLOW
    assert result.confidence == 0.88
    assert any("claim-abc" in e.snippet for e in result.evidence)


async def test_malformed_llm_response_returns_needs_review():
    """Malformed JSON from the LLM → NEEDS_REVIEW with LOW_CONFIDENCE."""
    prior = make_claim(statement="Water is wet.")
    validator, llm = _make_validator("this is not valid json {{{")
    claim = make_claim(statement="Water is dry.")
    context = make_workflow_context(accepted_claims=[prior])

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.NEEDS_REVIEW
    assert result.failure_mode == FailureMode.LOW_CONFIDENCE


async def test_consistency_validator_is_base_validator_instance():
    """ConsistencyValidator must implement the BaseValidator interface."""
    validator = ConsistencyValidator(llm_client=FakeLLMClient())
    assert isinstance(validator, BaseValidator)
    assert validator.name == "consistency"


async def test_llm_called_with_both_claims_in_prompt():
    """When prior claims exist, both claim statements appear in the LLM prompt."""
    prior = make_claim(statement="Gravity pulls objects downward.")
    validator, llm = _make_validator(
        _llm_response(contradicts=False, confidence=0.91, rationale="Consistent with physics.")
    )
    claim = make_claim(statement="Objects fall due to gravitational force.")
    context = make_workflow_context(accepted_claims=[prior])

    await validator.validate(claim, context)

    assert len(llm.calls) == 1
    call = llm.calls[0]
    combined = call["system"] + call["user"]
    assert "Gravity pulls objects downward" in combined
    assert "Objects fall due to gravitational force" in combined
