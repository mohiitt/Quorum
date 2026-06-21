"""Reasoning Validator — evaluates the logical validity of a claim using an LLM.

Supports a single-round analysis (default) and an optional debate round where
the LLM is run as both a skeptic and a defender before a synthesis pass produces
the final verdict.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from quorum.utils import strip_fences as _strip_fences
from quorum.contracts.interfaces import BaseValidator, LLMClient
from quorum.contracts.models import (
    Claim,
    Evidence,
    FailureMode,
    ValidatorName,
    ValidatorResult,
    Verdict,
    WorkflowContext,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a logical reasoning expert. Evaluate whether a claim has sound internal reasoning. "
    "A claim can be a factual data point, a market observation, or an investment assertion — judge it on its own terms. "
    "ACCEPT factual statements that are internally coherent and consistent (e.g., reporting a percentage, citing a trend). "
    "Only REJECT or flag NEEDS_REVIEW for: internally contradictory statements, conclusions that directly contradict their own premises, "
    "or claims that assert impossible/implausible logical relationships. "
    "Do NOT penalise a claim simply because it lacks a full investment recommendation or cites only partial data. "
    'Respond with JSON: {"verdict": "accepted"|"rejected"|"needs_review", "confidence": float, '
    '"failure_mode": "none"|"missing_reasoning"|"unsupported_conclusion"|"invalid_assumption"'
    '|"contradictory_logic", "rationale": str}'
)

_SKEPTIC_SYSTEM_PROMPT = "Find every logical flaw in this claim. Be harsh."

_DEFENDER_SYSTEM_PROMPT = "Justify this claim logically. Find the strongest argument for it."

_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a logical reasoning arbitrator. You have received a skeptic's critique and a "
    "defender's argument about a claim. Synthesize them into a balanced final verdict. "
    'Respond with JSON: {"verdict": "accepted"|"rejected"|"needs_review", "confidence": float, '
    '"failure_mode": "none"|"missing_reasoning"|"unsupported_conclusion"|"invalid_assumption"'
    '|"contradictory_logic", "rationale": str}'
)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_FAILURE_MODE_MAP: dict[str, FailureMode] = {
    "none": FailureMode.NONE,
    "missing_reasoning": FailureMode.MISSING_REASONING,
    "unsupported_conclusion": FailureMode.UNSUPPORTED_CONCLUSION,
    "invalid_assumption": FailureMode.INVALID_ASSUMPTION,
    "contradictory_logic": FailureMode.CONTRADICTORY_LOGIC,
}

_VERDICT_MAP: dict[str, Verdict] = {
    "accepted": Verdict.ACCEPTED,
    "rejected": Verdict.REJECTED,
    "needs_review": Verdict.NEEDS_REVIEW,
}

_PARSE_FAILURE: dict[str, Any] = {
    "verdict": "needs_review",
    "confidence": 0.4,
    "failure_mode": "missing_reasoning",
    "rationale": "Could not parse LLM response",
}


# ---------------------------------------------------------------------------
# ReasoningValidator
# ---------------------------------------------------------------------------


class ReasoningValidator(BaseValidator):
    """Validates the logical structure of a claim using an injected LLMClient."""

    def __init__(self, llm_client: LLMClient, debate: bool = False) -> None:
        self._llm = llm_client
        self._debate = debate

    @property
    def name(self) -> str:
        return ValidatorName.REASONING.value

    async def validate(self, claim: Claim, context: WorkflowContext) -> ValidatorResult:
        logger.info("[REASONING] claim=%.120s…", claim.statement)
        if self._debate:
            data = await self._debate_round(claim)
        else:
            data = await self._single_round(claim)

        verdict = _VERDICT_MAP.get(data.get("verdict", ""), Verdict.NEEDS_REVIEW)
        failure_mode = _FAILURE_MODE_MAP.get(
            data.get("failure_mode", ""), FailureMode.MISSING_REASONING
        )
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.4))))
        rationale = str(data.get("rationale", ""))
        logger.info(
            "[REASONING]   verdict=%s conf=%.2f failure=%s rationale=%.140s",
            verdict.value, confidence, data.get("failure_mode", "?"), rationale,
        )

        evidence = [
            Evidence(
                source="llm_analysis",
                snippet=rationale,
                quality=1.0,
            )
        ]

        return ValidatorResult(
            validator_name=ValidatorName.REASONING,
            verdict=verdict,
            confidence=confidence,
            failure_mode=failure_mode,
            evidence=evidence,
            rationale=rationale,
        )

    async def _single_round(self, claim: Claim) -> dict[str, Any]:
        raw = await self._llm.complete(_SYSTEM_PROMPT, claim.statement, max_tokens=2048)
        return self._parse_llm_response(raw)

    async def _debate_round(self, claim: Claim) -> dict[str, Any]:
        skeptic_raw = await self._llm.complete(_SKEPTIC_SYSTEM_PROMPT, claim.statement)
        defender_raw = await self._llm.complete(_DEFENDER_SYSTEM_PROMPT, claim.statement)

        synthesis_user_msg = (
            f"Claim: {claim.statement}\n\n"
            f"Skeptic analysis:\n{skeptic_raw}\n\n"
            f"Defender analysis:\n{defender_raw}"
        )
        synthesis_raw = await self._llm.complete(_SYNTHESIS_SYSTEM_PROMPT, synthesis_user_msg)
        return self._parse_llm_response(synthesis_raw)

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(_strip_fences(raw))
        except (json.JSONDecodeError, ValueError):
            logger.warning("ReasoningValidator: could not parse LLM response: %r", raw[:200])
            return dict(_PARSE_FAILURE)
