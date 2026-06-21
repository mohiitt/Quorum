"""Integration tests for the full QuorumPipeline."""

import pytest

from quorum.contracts.models import Verdict
from quorum.contracts.redis_keys import Keys
from quorum.fakes import (
    FakeEventBus,
    FakeStore,
    always_accept,
    always_reject,
    always_review,
    make_claim,
)
from quorum.pipeline import QuorumPipeline
from quorum.contracts.config import Settings


def _settings(**kwargs) -> Settings:
    base = {
        "redis_url": "redis://localhost",
        "anthropic_api_key": "",
        "sentry_dsn": "",
        "arize_api_key": "",
        "arize_space_key": "",
        "browserbase_api_key": "",
        "browserbase_project_id": "",
        "openweather_api_key": "",
        "pubmed_api_key": "",
        "consensus_accept_threshold": 0.70,
        "consensus_reject_threshold": 0.30,
    }
    base.update(kwargs)
    return Settings(**base)


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def bus():
    return FakeEventBus()


@pytest.fixture
def settings():
    return _settings()


class TestQuorumPipeline:
    async def test_accepted_claim_written_to_workflow_state(self, store, bus, settings):
        pipeline = QuorumPipeline(
            validators=[always_accept(), always_accept(), always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim(workflow_id="wf-int-001")
        result = await pipeline.process(claim)

        assert result.verdict == Verdict.ACCEPTED
        # Check workflow state list
        state = await store.list_all(Keys.workflow_state("wf-int-001"))
        assert claim.id in state

    async def test_rejected_claim_not_in_workflow_state(self, store, bus, settings):
        pipeline = QuorumPipeline(
            validators=[always_reject(), always_reject()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim(workflow_id="wf-int-002")
        result = await pipeline.process(claim)

        assert result.verdict == Verdict.REJECTED
        state = await store.list_all(Keys.workflow_state("wf-int-002"))
        assert claim.id not in state

    async def test_needs_review_goes_to_quarantine(self, store, bus, settings):
        # Force needs_review: mix accept+reject → score lands between thresholds
        settings_mid = _settings(
            consensus_accept_threshold=0.99,
            consensus_reject_threshold=0.01,
        )
        pipeline = QuorumPipeline(
            validators=[always_review()],
            store=store,
            event_bus=bus,
            settings=settings_mid,
        )
        claim = make_claim(workflow_id="wf-int-003")
        result = await pipeline.process(claim)

        assert result.verdict == Verdict.NEEDS_REVIEW
        quarantined = await store.list_all(Keys.PENDING_CLAIMS)
        assert len(quarantined) == 1

    async def test_provenance_recorded(self, store, bus, settings):
        pipeline = QuorumPipeline(
            validators=[always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim()
        await pipeline.process(claim)

        prov = await store.get_json(Keys.provenance(claim.id))
        assert prov is not None
        assert prov["claim_id"] == claim.id

    async def test_trust_updated(self, store, bus, settings):
        pipeline = QuorumPipeline(
            validators=[always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim(agent_id="agent-test-trust")
        await pipeline.process(claim)

        trust_raw = await store.get_json(Keys.trust("agent-test-trust"))
        assert trust_raw is not None
        assert trust_raw["total_claims"] == 1

    async def test_events_published(self, store, bus, settings):
        pipeline = QuorumPipeline(
            validators=[always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim()
        await pipeline.process(claim)

        event_types = [e["event_type"] for e in bus.events]
        assert "claim_submitted" in event_types
        assert "validator_result" in event_types
        assert "consensus_reached" in event_types

    async def test_multiple_validators_concurrent(self, store, bus, settings):
        """All 3 validators run concurrently and all results are included."""
        pipeline = QuorumPipeline(
            validators=[
                always_accept("source"),
                always_accept("consistency"),
                always_accept("reasoning"),
            ],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim()
        result = await pipeline.process(claim)

        assert len(result.validator_results) == 3

    async def test_recent_consensus_stored(self, store, bus, settings):
        """Consensus results are pushed to CONSENSUS_HISTORY list after pipeline runs."""
        pipeline = QuorumPipeline(
            validators=[always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        claim = make_claim(workflow_id="wf-recent-001")
        await pipeline.process(claim)

        history = await store.list_all(Keys.CONSENSUS_HISTORY)
        assert len(history) == 1
        assert history[0]["claim_id"] == claim.id
        assert "verdict" in history[0]

    async def test_consensus_history_capped_at_50(self, store, bus, settings):
        """CONSENSUS_HISTORY list is trimmed to at most 50 entries."""
        pipeline = QuorumPipeline(
            validators=[always_accept()],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        for i in range(55):
            await pipeline.process(make_claim(workflow_id=f"wf-cap-{i}"))

        history = await store.list_all(Keys.CONSENSUS_HISTORY)
        assert len(history) <= 50

    async def test_weather_demo_scenario(self, store, bus, settings):
        """Full weather demo: bad claim rejected, good claim accepted."""
        from quorum.fakes.fixtures import weather_claim_bad, weather_claim_good

        # Bad claim — all validators reject
        pipeline_reject = QuorumPipeline(
            validators=[always_reject("source"), always_reject("consistency"), always_reject("reasoning")],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        bad = weather_claim_bad()
        bad_result = await pipeline_reject.process(bad)
        assert bad_result.verdict == Verdict.REJECTED

        # Fallback agent submits the good claim — all validators accept
        pipeline_accept = QuorumPipeline(
            validators=[always_accept("source"), always_accept("consistency"), always_accept("reasoning")],
            store=store,
            event_bus=bus,
            settings=settings,
        )
        good = weather_claim_good()
        good_result = await pipeline_accept.process(good)
        assert good_result.verdict == Verdict.ACCEPTED

        # Only the good claim is in canonical workflow state
        state = await store.list_all(Keys.workflow_state(good.workflow_id))
        assert good.id in state
        assert bad.id not in state
