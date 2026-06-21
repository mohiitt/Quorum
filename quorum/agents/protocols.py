"""uAgents Protocol and Model message types for the Quorum validation network."""

from uagents import Model, Protocol


class ClaimSubmission(Model):
    """Message sent by worker agents to the Quorum gatekeeper."""

    claim: dict  # serialized Claim (dict for uAgents compat)
    workflow_id: str


class ValidationVerdict(Model):
    """Response from the Quorum gatekeeper back to the submitting agent."""

    claim_id: str
    verdict: str  # Verdict enum value
    score: float
    rationale: str
    quarantined: bool = False


class FallbackRequest(Model):
    """Sent to the fallback agent when a claim is rejected."""

    original_claim_id: str
    workflow_id: str
    failure_reason: str


class FallbackResponse(Model):
    """Response from the fallback agent with a corrected claim."""

    workflow_id: str
    corrected_claim: dict  # serialized Claim


# Shared protocol instance — include in both gatekeeper and any agent that
# sends ClaimSubmission or receives ValidationVerdict.
quorum_protocol = Protocol(name="QuorumValidation", version="1.0")
