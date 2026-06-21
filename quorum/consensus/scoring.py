"""Pure scoring functions for the consensus engine.

Formula:
    p_true_i  = P(claim is true) as estimated by validator i
              = confidence         if ACCEPTED
              = 1 − confidence     if REJECTED
              = 0.5                if NEEDS_REVIEW (uncertain)
    score_i   = reliability_i × p_true_i × mean_evidence_quality(evidence_i)
    total_score = mean(score_i for each validator)

This makes rejected validators *lower* the score (correct behaviour) and
needs_review validators contribute a neutral 0.5 weight.

No I/O, no side effects.
"""

from __future__ import annotations

from quorum.contracts.models import Evidence, ValidatorResult, Verdict


def mean_evidence_quality(evidence: list[Evidence]) -> float:
    """Return mean quality across *evidence*, defaulting to 1.0 when the list is empty."""
    if not evidence:
        return 1.0
    return sum(e.quality for e in evidence) / len(evidence)


def _p_true(result: ValidatorResult) -> float:
    """Interpret the validator verdict + confidence as P(claim is true)."""
    if result.verdict == Verdict.ACCEPTED:
        return result.confidence
    if result.verdict == Verdict.REJECTED:
        return 1.0 - result.confidence
    return 0.5  # NEEDS_REVIEW → uncertain


def compute_score(results: list[ValidatorResult]) -> float:
    """Compute the weighted consensus score from a list of validator results.

    Returns 0.0 for an empty list. Result is clamped to [0.0, 1.0].
    """
    if not results:
        return 0.0

    total = sum(
        r.reliability * _p_true(r) * mean_evidence_quality(r.evidence)
        for r in results
    )
    raw = total / len(results)
    return max(0.0, min(1.0, raw))


def apply_thresholds(score: float, accept: float, reject: float) -> Verdict:
    """Map *score* to a Verdict using the provided thresholds.

    score >= accept  → ACCEPTED
    score <= reject  → REJECTED
    otherwise        → NEEDS_REVIEW
    """
    if score >= accept:
        return Verdict.ACCEPTED
    if score <= reject:
        return Verdict.REJECTED
    return Verdict.NEEDS_REVIEW


def determine_verdict(score: float, settings) -> Verdict:
    """Alias used by ConsensusEngine — reads thresholds from settings."""
    return apply_thresholds(
        score,
        settings.consensus_accept_threshold,
        settings.consensus_reject_threshold,
    )
