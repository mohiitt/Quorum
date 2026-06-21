"""Consensus engine — aggregates validator results into a ConsensusResult."""

from __future__ import annotations

from quorum.contracts.config import Settings, get_settings
from quorum.contracts.errors import ConsensusError
from quorum.contracts.models import ConsensusResult, ValidatorResult, Verdict
from quorum.consensus.scoring import compute_score, determine_verdict


class ConsensusEngine:
    """Pure-computation engine that converts validator results into a consensus.

    All logic is synchronous; callers handle async I/O around this class.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, claim_id: str, validator_results: list[ValidatorResult]) -> ConsensusResult:
        """Run consensus over *validator_results* for the given *claim_id*.

        Raises:
            ConsensusError: if *validator_results* is empty.
        """
        if not validator_results:
            raise ConsensusError(
                f"Cannot compute consensus for claim '{claim_id}': no validator results provided"
            )

        score = compute_score(validator_results)
        verdict = determine_verdict(score, self._settings)
        rationale = self._build_rationale(score, verdict, validator_results)

        return ConsensusResult(
            claim_id=claim_id,
            verdict=verdict,
            score=round(score, 6),
            validator_results=validator_results,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_rationale(
        self,
        score: float,
        verdict: Verdict,
        results: list[ValidatorResult],
    ) -> str:
        accept = [r for r in results if r.verdict == Verdict.ACCEPTED]
        reject = [r for r in results if r.verdict == Verdict.REJECTED]
        review = [r for r in results if r.verdict == Verdict.NEEDS_REVIEW]

        lines: list[str] = [
            f"Consensus score: {score:.4f} → {verdict.value.upper()}.",
            f"Validators: {len(results)} total"
            f" | {len(accept)} accepted"
            f" | {len(reject)} rejected"
            f" | {len(review)} needs_review.",
        ]

        for r in results:
            name = r.validator_name if isinstance(r.validator_name, str) else r.validator_name.value
            lines.append(
                f"  [{name}] verdict={r.verdict.value}"
                f" confidence={r.confidence:.2f}"
                f" reliability={r.reliability:.2f}"
                + (f" — {r.rationale}" if r.rationale else "")
            )

        return "\n".join(lines)
