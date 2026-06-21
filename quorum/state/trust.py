"""Trust and reliability scoring for agents and validators."""

from __future__ import annotations

from datetime import datetime, timezone

from quorum.contracts.interfaces import BaseStore
from quorum.contracts.models import TrustScore, ValidatorReliability, Verdict
from quorum.contracts.redis_keys import Keys

_EMA_ALPHA = 0.1          # Validator reliability EMA smoothing factor
_TRUST_EMA_ALPHA = 0.15   # Agent trust EMA — slightly faster decay than validators
_DEFAULT_RELIABILITY = 0.8
_DEFAULT_TRUST_SCORE = 0.5


class TrustManager:
    """Updates and retrieves per-agent TrustScore and per-validator ValidatorReliability."""

    def __init__(self, store: BaseStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Agent trust
    # ------------------------------------------------------------------

    async def update_agent_trust(self, agent_id: str, verdict: Verdict) -> TrustScore:
        """Apply EMA update to agent trust score and update counters.

        EMA formula: new_score = (1 - alpha) * old_score + alpha * outcome
        where outcome = 1.0 (ACCEPTED), 0.0 (REJECTED), 0.5 (NEEDS_REVIEW).
        This gives time-decay so recent verdicts matter more than historical ones.
        """
        existing = await self.get_agent_trust(agent_id)

        total = existing.total_claims + 1
        accepted = existing.accepted_claims + (1 if verdict == Verdict.ACCEPTED else 0)
        rejected = existing.rejected_claims + (1 if verdict == Verdict.REJECTED else 0)

        if verdict == Verdict.ACCEPTED:
            outcome = 1.0
        elif verdict == Verdict.REJECTED:
            outcome = 0.0
        else:
            outcome = 0.5

        score = (1.0 - _TRUST_EMA_ALPHA) * existing.score + _TRUST_EMA_ALPHA * outcome

        updated = TrustScore(
            agent_id=agent_id,
            score=round(score, 6),
            total_claims=total,
            accepted_claims=accepted,
            rejected_claims=rejected,
            last_updated=datetime.now(timezone.utc),
        )
        await self._store.set_json(Keys.trust(agent_id), updated.model_dump(mode="json"))
        return updated

    async def get_agent_trust(self, agent_id: str) -> TrustScore:
        """Return stored TrustScore, or a fresh default if not yet recorded."""
        data = await self._store.get_json(Keys.trust(agent_id))
        if data is None:
            return TrustScore(agent_id=agent_id, score=_DEFAULT_TRUST_SCORE)
        return TrustScore.model_validate(data)

    async def get_all_trust_scores(self) -> list[TrustScore]:
        """Return TrustScore objects for every tracked agent."""
        keys = await self._store.keys_matching(Keys.TRUST_ALL_PATTERN)
        scores: list[TrustScore] = []
        for key in keys:
            data = await self._store.get_json(key)
            if data is not None:
                scores.append(TrustScore.model_validate(data))
        return scores

    # ------------------------------------------------------------------
    # Validator reliability
    # ------------------------------------------------------------------

    async def update_validator_reliability(
        self, validator_name: str, was_correct: bool
    ) -> ValidatorReliability:
        """Apply EMA update: new = 0.9 * old + 0.1 * outcome."""
        existing = await self.get_validator_reliability(validator_name)

        signal = 1.0 if was_correct else 0.0
        new_reliability = (1.0 - _EMA_ALPHA) * existing.reliability + _EMA_ALPHA * signal
        total = existing.total_validations + 1
        correct = existing.correct_validations + (1 if was_correct else 0)

        updated = ValidatorReliability(
            validator_name=validator_name,
            reliability=new_reliability,
            total_validations=total,
            correct_validations=correct,
            last_updated=datetime.now(timezone.utc),
        )
        await self._store.set_json(
            Keys.reliability(validator_name), updated.model_dump(mode="json")
        )
        return updated

    async def get_validator_reliability(self, validator_name: str) -> ValidatorReliability:
        """Return stored ValidatorReliability, or a fresh default."""
        data = await self._store.get_json(Keys.reliability(validator_name))
        if data is None:
            return ValidatorReliability(
                validator_name=validator_name, reliability=_DEFAULT_RELIABILITY
            )
        return ValidatorReliability.model_validate(data)

    async def get_all_reliabilities(self) -> list[ValidatorReliability]:
        """Return ValidatorReliability objects for every tracked validator."""
        keys = await self._store.keys_matching(Keys.RELIABILITY_ALL_PATTERN)
        reliabilities: list[ValidatorReliability] = []
        for key in keys:
            data = await self._store.get_json(key)
            if data is not None:
                reliabilities.append(ValidatorReliability.model_validate(data))
        return reliabilities
