"""Pydantic v2 data models — single source of truth for the entire system.

These models are shared by: uAgents message protocols, the FastAPI schema,
the Redis store, and the Next.js dashboard (via exported JSON schema).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Verdict(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class FailureMode(str, Enum):
    NO_EVIDENCE = "no_evidence"
    CONTRADICTS_SOURCE = "contradicts_source"
    CONTRADICTS_WORKFLOW = "contradicts_workflow"
    MISSING_REASONING = "missing_reasoning"
    UNSUPPORTED_CONCLUSION = "unsupported_conclusion"
    INVALID_ASSUMPTION = "invalid_assumption"
    CONTRADICTORY_LOGIC = "contradictory_logic"
    LOW_CONFIDENCE = "low_confidence"
    NONE = "none"


class ValidatorName(str, Enum):
    SOURCE = "source"
    CONSISTENCY = "consistency"
    REASONING = "reasoning"


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """A claim submitted by an agent for validation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    workflow_id: str
    statement: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {}


class WorkflowContext(BaseModel):
    """Snapshot of current workflow knowledge passed to validators."""

    workflow_id: str
    accepted_claims: list[Claim] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    """A piece of external or internal evidence supporting/refuting a claim."""

    source: str
    url: str | None = None
    snippet: str
    quality: float = Field(default=0.5, description="Evidence quality 0–1, clamped to [0, 1]")

    @field_validator("quality")
    @classmethod
    def clamp_quality(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ValidatorResult(BaseModel):
    """Output from a single validator."""

    validator_name: ValidatorName | str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0, description="Validator confidence 0–1")
    evidence: list[Evidence] = Field(default_factory=list)
    failure_mode: FailureMode = FailureMode.NONE
    reliability: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Historical reliability of this validator (updated by trust layer)",
    )
    rationale: str = ""


class ConsensusResult(BaseModel):
    """Aggregated output from the consensus engine."""

    claim_id: str
    verdict: Verdict
    score: float = Field(ge=0.0, le=1.0, description="Weighted consensus score 0–1")
    validator_results: list[ValidatorResult]
    rationale: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProvenanceRecord(BaseModel):
    """Immutable audit record stored for every processed claim."""

    claim_id: str
    claim: Claim
    consensus_result: ConsensusResult
    validator_names: list[str]
    final_verdict: Verdict
    confidence_score: float
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrustScore(BaseModel):
    """Per-agent trust metrics updated after each consensus round."""

    agent_id: str
    score: float = Field(ge=0.0, le=1.0, default=0.5)
    total_claims: int = 0
    accepted_claims: int = 0
    rejected_claims: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def acceptance_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return self.accepted_claims / self.total_claims


class ValidatorReliability(BaseModel):
    """Per-validator reliability tracked over time."""

    validator_name: str
    reliability: float = Field(ge=0.0, le=1.0, default=0.8)
    total_validations: int = 0
    correct_validations: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# API response shapes (used by FastAPI and the dashboard)
# ---------------------------------------------------------------------------


class ValidationResponse(BaseModel):
    """Response from POST /claims/validate."""

    claim_id: str
    verdict: Verdict
    score: float
    rationale: str
    quarantined: bool = False
    provenance_url: str | None = None


class WorkflowStateResponse(BaseModel):
    """Response from GET /workflows/{workflow_id}/state."""

    workflow_id: str
    accepted_claims: list[Claim]
    pending_claims: list[Claim]
    agent_trust_scores: list[TrustScore]


class ConsensusEvent(BaseModel):
    """WebSocket event pushed to the dashboard."""

    event_type: str  # "claim_submitted" | "validator_result" | "consensus_reached" | "quarantined"
    claim_id: str
    workflow_id: str
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
