"""Tests for TrustManager using FakeStore."""

from __future__ import annotations

import pytest

from quorum.contracts.models import Verdict
from quorum.fakes.store import FakeStore
from quorum.state.trust import TrustManager

_DEFAULT_TRUST = 0.5
_DEFAULT_RELIABILITY = 0.8


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def trust(store: FakeStore) -> TrustManager:
    return TrustManager(store)


# ---------------------------------------------------------------------------
# Agent trust
# ---------------------------------------------------------------------------


async def test_new_agent_starts_with_default_score(trust: TrustManager) -> None:
    """A brand-new agent has the default trust score of 0.5."""
    ts = await trust.get_agent_trust("agent-new")
    assert ts.score == pytest.approx(_DEFAULT_TRUST)
    assert ts.total_claims == 0


async def test_accepted_verdict_increases_score(trust: TrustManager) -> None:
    """An ACCEPTED verdict raises score via EMA: (1-0.15)*0.5 + 0.15*1.0 = 0.575."""
    ts = await trust.update_agent_trust("agent-a", Verdict.ACCEPTED)
    assert ts.accepted_claims == 1
    assert ts.total_claims == 1
    assert ts.score == pytest.approx(0.85 * 0.5 + 0.15 * 1.0)


async def test_rejected_verdict_records_correctly(trust: TrustManager) -> None:
    """A REJECTED verdict lowers score via EMA: (1-0.15)*0.5 + 0.15*0.0 = 0.425."""
    ts = await trust.update_agent_trust("agent-b", Verdict.REJECTED)
    assert ts.rejected_claims == 1
    assert ts.accepted_claims == 0
    assert ts.total_claims == 1
    assert ts.score == pytest.approx(0.85 * 0.5 + 0.15 * 0.0)


async def test_multiple_verdicts_ema_accumulates(trust: TrustManager) -> None:
    """EMA score updates sequentially: ACCEPTED, ACCEPTED, REJECTED."""
    agent = "agent-multi"
    # step 1: ACCEPTED -> 0.85*0.5 + 0.15*1.0 = 0.575
    # step 2: ACCEPTED -> 0.85*0.575 + 0.15*1.0 = 0.63875
    # step 3: REJECTED -> 0.85*0.63875 + 0.15*0.0 ≈ 0.54294
    await trust.update_agent_trust(agent, Verdict.ACCEPTED)
    await trust.update_agent_trust(agent, Verdict.ACCEPTED)
    ts = await trust.update_agent_trust(agent, Verdict.REJECTED)

    assert ts.total_claims == 3
    assert ts.accepted_claims == 2
    assert ts.rejected_claims == 1
    expected = 0.85 * (0.85 * (0.85 * 0.5 + 0.15 * 1.0) + 0.15 * 1.0) + 0.15 * 0.0
    assert ts.score == pytest.approx(expected, rel=1e-5)


async def test_get_all_trust_scores_returns_all_agents(trust: TrustManager) -> None:
    """get_all_trust_scores includes every agent that has been updated."""
    await trust.update_agent_trust("alpha", Verdict.ACCEPTED)
    await trust.update_agent_trust("beta", Verdict.REJECTED)

    all_scores = await trust.get_all_trust_scores()
    agent_ids = {ts.agent_id for ts in all_scores}
    assert "alpha" in agent_ids
    assert "beta" in agent_ids


# ---------------------------------------------------------------------------
# Validator reliability
# ---------------------------------------------------------------------------


async def test_new_validator_starts_with_default_reliability(trust: TrustManager) -> None:
    """A never-seen validator has the default reliability of 0.8."""
    vr = await trust.get_validator_reliability("source")
    assert vr.reliability == pytest.approx(_DEFAULT_RELIABILITY)
    assert vr.total_validations == 0


async def test_correct_validation_ema_update(trust: TrustManager) -> None:
    """A correct validation applies EMA: 0.9 * 0.8 + 0.1 * 1.0 = 0.82."""
    vr = await trust.update_validator_reliability("source", was_correct=True)
    expected = 0.9 * _DEFAULT_RELIABILITY + 0.1 * 1.0
    assert vr.reliability == pytest.approx(expected)
    assert vr.correct_validations == 1
    assert vr.total_validations == 1


async def test_incorrect_validation_ema_update(trust: TrustManager) -> None:
    """An incorrect validation applies EMA: 0.9 * 0.8 + 0.1 * 0.0 = 0.72."""
    vr = await trust.update_validator_reliability("reasoning", was_correct=False)
    expected = 0.9 * _DEFAULT_RELIABILITY + 0.1 * 0.0
    assert vr.reliability == pytest.approx(expected)
    assert vr.correct_validations == 0


async def test_get_all_reliabilities_returns_all_validators(trust: TrustManager) -> None:
    """get_all_reliabilities returns all validators that have been updated."""
    await trust.update_validator_reliability("source", was_correct=True)
    await trust.update_validator_reliability("consistency", was_correct=False)

    all_rel = await trust.get_all_reliabilities()
    names = {r.validator_name for r in all_rel}
    assert "source" in names
    assert "consistency" in names


async def test_agent_trust_ema_decay(trust: TrustManager) -> None:
    """Regression: agent trust uses EMA not acceptance-rate; consecutive rejects decay score."""
    agent = "agent-ema-decay"
    # Give it a good reputation first
    for _ in range(5):
        await trust.update_agent_trust(agent, Verdict.ACCEPTED)
    good_ts = await trust.get_agent_trust(agent)
    # Then a run of rejections should pull the score down noticeably
    for _ in range(5):
        await trust.update_agent_trust(agent, Verdict.REJECTED)
    bad_ts = await trust.get_agent_trust(agent)
    assert bad_ts.score < good_ts.score, "EMA decay should lower score after consecutive rejections"
    # Score should have decayed significantly but not to zero immediately (EMA smoothing)
    assert bad_ts.score > 0.0, "Score should not instantly drop to zero"


async def test_needs_review_verdict_neutral_ema(trust: TrustManager) -> None:
    """NEEDS_REVIEW verdict uses outcome=0.5, keeping score near default."""
    ts = await trust.update_agent_trust("agent-review", Verdict.NEEDS_REVIEW)
    expected = 0.85 * 0.5 + 0.15 * 0.5
    assert ts.score == pytest.approx(expected)
