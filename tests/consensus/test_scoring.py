"""Unit tests for quorum.consensus.scoring — pure functions, no I/O."""

from __future__ import annotations

import pytest

from quorum.consensus.scoring import compute_score, determine_verdict
from quorum.contracts.config import Settings
from quorum.contracts.models import Evidence, ValidatorResult, ValidatorName, Verdict, FailureMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(accept: float = 0.70, reject: float = 0.30) -> Settings:
    return Settings(
        CONSENSUS_ACCEPT_THRESHOLD=accept,
        CONSENSUS_REJECT_THRESHOLD=reject,
    )


def _result(
    confidence: float = 0.8,
    reliability: float = 0.9,
    evidence_qualities: list[float] | None = None,
    verdict: Verdict = Verdict.ACCEPTED,
) -> ValidatorResult:
    evidence = (
        [Evidence(source="test", snippet="s", quality=q) for q in evidence_qualities]
        if evidence_qualities is not None
        else []
    )
    return ValidatorResult(
        validator_name=ValidatorName.SOURCE,
        verdict=verdict,
        confidence=confidence,
        reliability=reliability,
        evidence=evidence,
        failure_mode=FailureMode.NONE,
    )


# ---------------------------------------------------------------------------
# compute_score
# ---------------------------------------------------------------------------


class TestComputeScore:
    def test_single_result_no_evidence_uses_default_quality(self) -> None:
        # evidence empty → avg quality defaults to 1.0 (no evidence penalty)
        r = _result(confidence=0.8, reliability=1.0, evidence_qualities=None)
        score = compute_score([r])
        assert score == pytest.approx(1.0 * 0.8 * 1.0)

    def test_single_result_with_evidence(self) -> None:
        r = _result(confidence=0.8, reliability=0.9, evidence_qualities=[1.0])
        score = compute_score([r])
        assert score == pytest.approx(0.9 * 0.8 * 1.0)

    def test_multiple_results_averages_correctly(self) -> None:
        r1 = _result(confidence=1.0, reliability=1.0, evidence_qualities=[1.0])
        r2 = _result(confidence=0.0, reliability=1.0, evidence_qualities=[1.0])
        score = compute_score([r1, r2])
        # (1*1*1 + 1*0*1) / 2 = 0.5
        assert score == pytest.approx(0.5)

    def test_avg_evidence_quality_over_multiple_pieces(self) -> None:
        r = _result(confidence=1.0, reliability=1.0, evidence_qualities=[0.0, 1.0])
        score = compute_score([r])
        assert score == pytest.approx(0.5)

    def test_all_zeros_gives_zero_score(self) -> None:
        r = _result(confidence=0.0, reliability=0.0, evidence_qualities=[0.0])
        assert compute_score([r]) == pytest.approx(0.0)

    def test_all_ones_gives_one_score(self) -> None:
        r = _result(confidence=1.0, reliability=1.0, evidence_qualities=[1.0])
        assert compute_score([r]) == pytest.approx(1.0)

    def test_three_validators_mean(self) -> None:
        results = [
            _result(confidence=0.9, reliability=0.9, evidence_qualities=[1.0]),   # 0.81
            _result(confidence=0.8, reliability=0.8, evidence_qualities=[1.0]),   # 0.64
            _result(confidence=0.7, reliability=0.7, evidence_qualities=[1.0]),   # 0.49
        ]
        expected = (0.81 + 0.64 + 0.49) / 3
        assert compute_score(results) == pytest.approx(expected, rel=1e-6)

    def test_empty_list_returns_zero(self) -> None:
        # empty list → 0.0 (no ZeroDivisionError), engine raises separately
        assert compute_score([]) == 0.0


# ---------------------------------------------------------------------------
# determine_verdict
# ---------------------------------------------------------------------------


class TestDetermineVerdict:
    def test_above_accept_threshold_returns_accepted(self) -> None:
        assert determine_verdict(0.75, _settings()) == Verdict.ACCEPTED

    def test_exactly_at_accept_threshold_returns_accepted(self) -> None:
        assert determine_verdict(0.70, _settings()) == Verdict.ACCEPTED

    def test_below_reject_threshold_returns_rejected(self) -> None:
        assert determine_verdict(0.25, _settings()) == Verdict.REJECTED

    def test_exactly_at_reject_threshold_returns_rejected(self) -> None:
        assert determine_verdict(0.30, _settings()) == Verdict.REJECTED

    def test_between_thresholds_returns_needs_review(self) -> None:
        assert determine_verdict(0.50, _settings()) == Verdict.NEEDS_REVIEW

    def test_just_above_reject_threshold_is_needs_review(self) -> None:
        assert determine_verdict(0.31, _settings()) == Verdict.NEEDS_REVIEW

    def test_just_below_accept_threshold_is_needs_review(self) -> None:
        assert determine_verdict(0.69, _settings()) == Verdict.NEEDS_REVIEW

    def test_custom_thresholds_respected(self) -> None:
        s = _settings(accept=0.90, reject=0.10)
        assert determine_verdict(0.95, s) == Verdict.ACCEPTED
        assert determine_verdict(0.05, s) == Verdict.REJECTED
        assert determine_verdict(0.50, s) == Verdict.NEEDS_REVIEW
