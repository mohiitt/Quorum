"""Fake validators for testing — return canned verdicts without any I/O."""

from __future__ import annotations

from quorum.contracts.interfaces import BaseValidator
from quorum.contracts.models import (
    Claim,
    Evidence,
    FailureMode,
    ValidatorResult,
    ValidatorName,
    Verdict,
    WorkflowContext,
)


class FakeValidator(BaseValidator):
    """Configurable fake validator that returns a preset result."""

    def __init__(
        self,
        *,
        verdict: Verdict = Verdict.ACCEPTED,
        confidence: float = 0.9,
        failure_mode: FailureMode = FailureMode.NONE,
        validator_name: str = "fake",
        reliability: float = 0.9,
        evidence: list[Evidence] | None = None,
        rationale: str = "Fake validator result",
    ) -> None:
        self._verdict = verdict
        self._confidence = confidence
        self._failure_mode = failure_mode
        self._name = validator_name
        self._reliability = reliability
        self._evidence = evidence or [
            Evidence(source="fake", snippet="Fake evidence snippet", quality=0.9)
        ]
        self._rationale = rationale

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, claim: Claim, context: WorkflowContext) -> ValidatorResult:
        return ValidatorResult(
            validator_name=self._name,
            verdict=self._verdict,
            confidence=self._confidence,
            failure_mode=self._failure_mode,
            reliability=self._reliability,
            evidence=self._evidence,
            rationale=self._rationale,
        )


def always_accept(name: str = "fake_accept") -> FakeValidator:
    return FakeValidator(verdict=Verdict.ACCEPTED, confidence=0.95, validator_name=name)


def always_reject(name: str = "fake_reject") -> FakeValidator:
    # Low confidence + low reliability so the weighted score (reliability × confidence × quality)
    # falls below the default reject threshold (0.30).
    return FakeValidator(
        verdict=Verdict.REJECTED,
        confidence=0.1,
        failure_mode=FailureMode.NO_EVIDENCE,
        validator_name=name,
        reliability=0.3,
        evidence=[Evidence(source="fake", snippet="No evidence found", quality=0.1)],
        rationale="Rejected by fake validator",
    )


def always_review(name: str = "fake_review") -> FakeValidator:
    return FakeValidator(
        verdict=Verdict.NEEDS_REVIEW,
        confidence=0.50,
        failure_mode=FailureMode.LOW_CONFIDENCE,
        validator_name=name,
    )
