"""Consistency Validator — checks new claims against accepted workflow claims.

Uses an LLM to detect contradictions between a new claim and previously
accepted claims in the same workflow.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from quorum.utils import strip_fences as _strip_fences
from quorum.contracts.config import Settings, get_settings
from quorum.contracts.errors import ConfigurationError
from quorum.contracts.interfaces import BaseValidator, LLMClient
from quorum.contracts.models import (
    Claim,
    Evidence,
    FailureMode,
    ValidatorResult,
    Verdict,
    WorkflowContext,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a logical consistency checker for a multi-agent workflow system.
Your task is to determine whether a new claim contradicts any previously accepted claims.

Respond ONLY with valid JSON in this exact format:
{
  "contradicts": true or false,
  "confidence": <float between 0.0 and 1.0>,
  "rationale": "<brief explanation>",
  "contradicted_claim_id": "<id of the contradicted claim, or null if none>"
}

Do not include any text outside of the JSON object.
"""


def _build_user_message(new_claim: Claim, accepted_claims: list[Claim]) -> str:
    prior_text = "\n".join(
        f"  - [id={c.id}] {c.statement}" for c in accepted_claims
    )
    return (
        f"New claim to evaluate:\n"
        f"  Statement: {new_claim.statement}\n\n"
        f"Previously accepted claims in this workflow:\n"
        f"{prior_text}\n\n"
        f"Does the new claim contradict any of the accepted claims?"
    )


class AnthropicLLMClient(LLMClient):
    """Production LLM client backed by Anthropic Claude."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model or get_settings().anthropic_model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        )
        return message.content[0].text  # type: ignore[union-attr]


class ConsistencyValidator(BaseValidator):
    """Validates that a new claim does not contradict accepted workflow claims."""

    @property
    def name(self) -> str:
        return "consistency"

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        if llm_client is None:
            api_key = self._settings.anthropic_api_key
            if not api_key:
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY is not set. Provide an llm_client or set the env var."
                )
            self._llm = AnthropicLLMClient(api_key=api_key)
        else:
            self._llm = llm_client

    async def validate(self, claim: Claim, context: WorkflowContext) -> ValidatorResult:
        accepted = context.accepted_claims

        logger.info(
            "[CONSISTENCY] workflow=%s | %d prior accepted claim(s) | new claim=%.100s…",
            claim.workflow_id, len(accepted), claim.statement,
        )
        for i, prior in enumerate(accepted):
            logger.info("[CONSISTENCY]   prior[%d]: %.120s", i, prior.statement)

        if not accepted:
            logger.info("[CONSISTENCY]   → trivially consistent (no prior claims)")
            return ValidatorResult(
                validator_name=self.name,
                verdict=Verdict.ACCEPTED,
                confidence=0.9,
                failure_mode=FailureMode.NONE,
                rationale="No prior accepted claims in this workflow — claim is trivially consistent.",
            )

        user_message = _build_user_message(claim, accepted)

        try:
            raw = await self._llm.complete(
                _SYSTEM_PROMPT,
                user_message,
                max_tokens=512,
                temperature=0.0,
            )
            logger.info("[CONSISTENCY]   LLM raw response: %.200s", raw.strip())
            parsed: dict[str, Any] = json.loads(_strip_fences(raw))
            contradicts: bool = parsed["contradicts"]
            confidence: float = float(parsed["confidence"])
            rationale: str = parsed.get("rationale", "")
            contradicted_id: str | None = parsed.get("contradicted_claim_id")
            logger.info(
                "[CONSISTENCY]   contradicts=%s conf=%.2f rationale=%.140s",
                contradicts, confidence, rationale,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("[CONSISTENCY]   malformed LLM response — %s", exc)
            return ValidatorResult(
                validator_name=self.name,
                verdict=Verdict.NEEDS_REVIEW,
                confidence=0.0,
                failure_mode=FailureMode.LOW_CONFIDENCE,
                rationale="LLM returned a malformed response; manual review required.",
            )

        if contradicts:
            evidence: list[Evidence] = []
            if contradicted_id:
                evidence = [
                    Evidence(
                        source="consistency_validator",
                        snippet=f"Contradicts accepted claim {contradicted_id}",
                        quality=1.0,
                    )
                ]
            return ValidatorResult(
                validator_name=self.name,
                verdict=Verdict.REJECTED,
                confidence=confidence,
                failure_mode=FailureMode.CONTRADICTS_WORKFLOW,
                evidence=evidence,
                rationale=rationale,
            )

        return ValidatorResult(
            validator_name=self.name,
            verdict=Verdict.ACCEPTED,
            confidence=confidence,
            failure_mode=FailureMode.NONE,
            rationale=rationale,
        )
