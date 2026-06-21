"""Centralized Redis key builders.

All Redis key strings are defined here so every component uses identical
keys without string-formatting scattered across the codebase.
"""

from __future__ import annotations


class Keys:
    """Namespace for all Quorum Redis keys."""

    # --- Pending / quarantined claims (list) ---
    PENDING_CLAIMS = "quorum:pending_claims"

    # --- Canonical workflow state (hash or JSON string per claim) ---
    @staticmethod
    def workflow_state(workflow_id: str) -> str:
        """List of accepted claim IDs for a workflow."""
        return f"quorum:state:{workflow_id}"

    @staticmethod
    def workflow_claim(workflow_id: str, claim_id: str) -> str:
        """Full Claim JSON stored in workflow state."""
        return f"quorum:state:{workflow_id}:claim:{claim_id}"

    # --- Provenance ---
    @staticmethod
    def provenance(claim_id: str) -> str:
        """ProvenanceRecord JSON for a given claim."""
        return f"quorum:provenance:{claim_id}"

    # --- Consensus history (list of ConsensusResult JSON, capped at 50) ---
    CONSENSUS_HISTORY = "quorum:consensus_history"
    CONSENSUS_HISTORY_MAX = 50

    @staticmethod
    def consensus_result(claim_id: str) -> str:
        """Latest ConsensusResult JSON for a given claim."""
        return f"quorum:consensus:{claim_id}"

    # --- Agent trust ---
    @staticmethod
    def trust(agent_id: str) -> str:
        """TrustScore JSON for a given agent."""
        return f"quorum:trust:{agent_id}"

    # Pattern to scan all trust scores:
    TRUST_ALL_PATTERN = "quorum:trust:*"

    # --- Validator reliability ---
    @staticmethod
    def reliability(validator_name: str) -> str:
        """ValidatorReliability JSON for a given validator."""
        return f"quorum:reliability:{validator_name}"

    RELIABILITY_ALL_PATTERN = "quorum:reliability:*"

    # --- Event stream (pub/sub channel) ---
    CONSENSUS_EVENTS_CHANNEL = "quorum:events:consensus"
