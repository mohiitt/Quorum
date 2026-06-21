"""Fake ValidationPipeline for testing API routes and uAgent handlers."""

from __future__ import annotations

from quorum.contracts.interfaces import ValidationPipeline
from quorum.contracts.models import Claim, ConsensusResult, Verdict
from quorum.fakes.fixtures import make_validator_result


class FakePipeline(ValidationPipeline):
    """Returns a preset ConsensusResult without running any validators."""

    def __init__(
        self,
        verdict: Verdict = Verdict.ACCEPTED,
        score: float = 0.85,
        rationale: str = "Fake pipeline result",
    ) -> None:
        self._verdict = verdict
        self._score = score
        self._rationale = rationale
        self.processed: list[Claim] = []

    async def process(self, claim: Claim) -> ConsensusResult:
        self.processed.append(claim)
        return ConsensusResult(
            claim_id=claim.id,
            verdict=self._verdict,
            score=self._score,
            validator_results=[make_validator_result(verdict=self._verdict)],
            rationale=self._rationale,
        )
