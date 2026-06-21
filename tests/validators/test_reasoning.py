"""Tests for ReasoningValidator.

All LLM calls are intercepted by FakeLLMClient — no real API calls are made.
pytest-asyncio is configured with asyncio_mode="auto" (see pyproject.toml).
"""

from __future__ import annotations

import json

import pytest

from quorum.contracts.interfaces import BaseValidator, LLMClient
from quorum.contracts.models import FailureMode, ValidatorName, Verdict
from quorum.fakes import FakeLLMClient, make_claim, make_workflow_context
from quorum.validators.reasoning import ReasoningValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(
    verdict: str = "accepted",
    confidence: float = 0.9,
    failure_mode: str = "none",
    rationale: str = "Logically sound.",
) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "confidence": confidence,
            "failure_mode": failure_mode,
            "rationale": rationale,
        }
    )


class MultiResponseFakeLLMClient(LLMClient):
    """Returns successive responses from a list; repeats the last one on overflow."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        self.calls.append({"system": system_prompt, "user": user_message})
        idx = min(len(self.calls) - 1, len(self._responses) - 1)
        return self._responses[idx]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def claim():
    return make_claim(statement="Renewable energy will reduce costs by 50% within 5 years.")


@pytest.fixture
def context():
    return make_workflow_context()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_accepted_verdict(claim, context):
    """LLM returns accepted JSON → result is ACCEPTED with high confidence."""
    llm = FakeLLMClient(_json_response(verdict="accepted", confidence=0.92))
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.ACCEPTED
    assert result.confidence == pytest.approx(0.92)
    assert result.failure_mode == FailureMode.NONE
    assert result.validator_name == ValidatorName.REASONING


async def test_rejected_missing_reasoning(claim, context):
    """LLM returns rejected+missing_reasoning → REJECTED + correct FailureMode."""
    llm = FakeLLMClient(
        _json_response(
            verdict="rejected",
            confidence=0.85,
            failure_mode="missing_reasoning",
            rationale="No causal chain provided.",
        )
    )
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.REJECTED
    assert result.failure_mode == FailureMode.MISSING_REASONING


async def test_invalid_json_returns_needs_review(claim, context):
    """LLM returns invalid JSON → NEEDS_REVIEW with confidence 0.4."""
    llm = FakeLLMClient("this is not valid json }{")
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    assert result.verdict == Verdict.NEEDS_REVIEW
    assert result.confidence == pytest.approx(0.4)
    assert result.rationale == "Could not parse LLM response"


async def test_debate_mode_calls_llm_three_times(claim, context):
    """Debate mode: LLM called exactly 3 times (skeptic, defender, synthesis)."""
    final_response = _json_response(verdict="accepted", confidence=0.88, rationale="Balanced view.")
    llm = MultiResponseFakeLLMClient(
        [
            "Skeptic critique: premise is weak.",
            "Defender argument: the evidence supports this.",
            final_response,
        ]
    )
    validator = ReasoningValidator(llm, debate=True)

    result = await validator.validate(claim, context)

    assert len(llm.calls) == 3, f"Expected 3 LLM calls, got {len(llm.calls)}"
    assert result.verdict == Verdict.ACCEPTED


async def test_debate_mode_disabled_calls_llm_once(claim, context):
    """debate=False → only one LLM call (default behaviour)."""
    llm = FakeLLMClient(_json_response(verdict="accepted", confidence=0.8))
    validator = ReasoningValidator(llm, debate=False)

    await validator.validate(claim, context)

    assert len(llm.calls) == 1


async def test_all_failure_modes_mapped(claim, context):
    """All known failure_mode strings are mapped to the correct FailureMode enum."""
    cases = [
        ("none", FailureMode.NONE),
        ("missing_reasoning", FailureMode.MISSING_REASONING),
        ("unsupported_conclusion", FailureMode.UNSUPPORTED_CONCLUSION),
        ("invalid_assumption", FailureMode.INVALID_ASSUMPTION),
        ("contradictory_logic", FailureMode.CONTRADICTORY_LOGIC),
    ]
    for fm_str, expected_enum in cases:
        llm = FakeLLMClient(_json_response(failure_mode=fm_str))
        validator = ReasoningValidator(llm)
        result = await validator.validate(claim, context)
        assert result.failure_mode == expected_enum, (
            f"failure_mode '{fm_str}' should map to {expected_enum}, got {result.failure_mode}"
        )


async def test_unknown_failure_mode_defaults_to_missing_reasoning(claim, context):
    """An unrecognised failure_mode string falls back to MISSING_REASONING."""
    llm = FakeLLMClient(_json_response(failure_mode="totally_unknown_mode"))
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    assert result.failure_mode == FailureMode.MISSING_REASONING


async def test_evidence_includes_llm_analysis_source(claim, context):
    """ValidatorResult must contain at least one Evidence item with source='llm_analysis'."""
    llm = FakeLLMClient(_json_response(rationale="Sound logical structure."))
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    sources = [e.source for e in result.evidence]
    assert "llm_analysis" in sources, f"Expected 'llm_analysis' in evidence sources, got {sources}"


async def test_evidence_quality_is_constant_one(claim, context):
    """Evidence quality must be 1.0 (fixed) so confidence is not double-penalised in compute_score."""
    llm = FakeLLMClient(_json_response(confidence=0.76))
    validator = ReasoningValidator(llm)

    result = await validator.validate(claim, context)

    llm_evidence = next(e for e in result.evidence if e.source == "llm_analysis")
    assert llm_evidence.quality == pytest.approx(1.0)


async def test_reasoning_validator_is_base_validator():
    """ReasoningValidator is a proper subclass of BaseValidator."""
    llm = FakeLLMClient()
    validator = ReasoningValidator(llm)
    assert isinstance(validator, BaseValidator)
    assert validator.name == ValidatorName.REASONING.value
