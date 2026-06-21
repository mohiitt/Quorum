"""Sample Claim, WorkflowContext, and ValidatorResult factories."""

from __future__ import annotations

from quorum.contracts.models import (
    Claim,
    Evidence,
    FailureMode,
    ValidatorResult,
    ValidatorName,
    Verdict,
    WorkflowContext,
)


def make_claim(
    *,
    agent_id: str = "agent-weather-001",
    workflow_id: str = "wf-demo-001",
    statement: str = "There is a 0% chance of rain tomorrow.",
    payload: dict | None = None,
    claim_id: str | None = None,
) -> Claim:
    """Factory for test Claim instances."""
    c = Claim(
        agent_id=agent_id,
        workflow_id=workflow_id,
        statement=statement,
        payload=payload or {"source": "weather-api", "confidence": 0.42},
    )
    if claim_id:
        c = c.model_copy(update={"id": claim_id})
    return c


def make_workflow_context(
    *,
    workflow_id: str = "wf-demo-001",
    accepted_claims: list[Claim] | None = None,
) -> WorkflowContext:
    """Factory for test WorkflowContext instances."""
    return WorkflowContext(
        workflow_id=workflow_id,
        accepted_claims=accepted_claims or [],
    )


def make_validator_result(
    *,
    validator_name: str = ValidatorName.SOURCE,
    verdict: Verdict = Verdict.ACCEPTED,
    confidence: float = 0.85,
    failure_mode: FailureMode = FailureMode.NONE,
    reliability: float = 0.9,
    rationale: str = "Test result",
) -> ValidatorResult:
    """Factory for test ValidatorResult instances."""
    return ValidatorResult(
        validator_name=validator_name,
        verdict=verdict,
        confidence=confidence,
        failure_mode=failure_mode,
        reliability=reliability,
        evidence=[Evidence(source="test", snippet="Test evidence", quality=0.8)],
        rationale=rationale,
    )


# --- Pre-built scenarios ---

def weather_claim_bad() -> Claim:
    """The hallucinated '0% rain' claim from the demo scenario."""
    return make_claim(
        agent_id="agent-weather-001",
        statement="There is a 0% chance of rain tomorrow.",
        payload={"forecast": {"rain_probability": 0.0, "source": "hallucinated"}},
    )


def weather_claim_good() -> Claim:
    """The corrected weather claim from the fallback agent."""
    return make_claim(
        agent_id="agent-weather-fallback",
        statement="There is a 75% chance of rain tomorrow based on NOAA data.",
        payload={"forecast": {"rain_probability": 0.75, "source": "NOAA"}},
    )
