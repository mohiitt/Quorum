"""Tests for FastAPI REST routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from quorum.api.dependencies import set_event_bus, set_pipeline, set_store
from quorum.api.main import app
from quorum.contracts.models import Verdict
from quorum.contracts.redis_keys import Keys
from quorum.fakes import FakeEventBus, FakePipeline, FakeStore, FakeValidator, make_claim


@pytest.fixture(autouse=True)
def inject_fakes():
    store = FakeStore()
    set_pipeline(FakePipeline(verdict=Verdict.ACCEPTED, score=0.85))
    set_store(store)
    set_event_bus(FakeEventBus())
    yield store


@pytest.fixture
def client(inject_fakes):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health(client):
    async with client as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_validate_claim_accepted(client):
    async with client as c:
        resp = await c.post(
            "/claims/validate",
            json={
                "agent_id": "agent-weather-001",
                "workflow_id": "wf-001",
                "statement": "There is 0% chance of rain.",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "accepted"
    assert data["score"] == pytest.approx(0.85)
    assert "claim_id" in data
    assert data["provenance_url"].startswith("/claims/")


async def test_validate_claim_rejected(client):
    set_pipeline(FakePipeline(verdict=Verdict.REJECTED, score=0.15))
    async with client as c:
        resp = await c.post(
            "/claims/validate",
            json={
                "agent_id": "a1",
                "workflow_id": "wf-001",
                "statement": "Test claim",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "rejected"


async def test_validate_claim_missing_fields(client):
    async with client as c:
        resp = await c.post("/claims/validate", json={"agent_id": "a1"})
    assert resp.status_code == 422


async def test_get_provenance_not_found(client):
    async with client as c:
        resp = await c.get("/claims/nonexistent-claim-id/provenance")
    assert resp.status_code == 404


async def test_get_provenance_found(inject_fakes, client):
    store: FakeStore = inject_fakes
    claim = make_claim(claim_id="test-claim-123")
    await store.set_json(
        Keys.provenance("test-claim-123"),
        {"claim_id": "test-claim-123", "final_verdict": "accepted"},
    )
    async with client as c:
        resp = await c.get("/claims/test-claim-123/provenance")
    assert resp.status_code == 200
    assert resp.json()["claim_id"] == "test-claim-123"


async def test_get_agents_trust_empty(client):
    async with client as c:
        resp = await c.get("/agents/trust")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_agents_trust_with_data(inject_fakes, client):
    store: FakeStore = inject_fakes
    await store.set_json(
        Keys.trust("agent-001"),
        {"agent_id": "agent-001", "score": 0.8, "total_claims": 10},
    )
    async with client as c:
        resp = await c.get("/agents/trust")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["agent_id"] == "agent-001"


async def test_quarantine_empty(client):
    async with client as c:
        resp = await c.get("/claims/quarantine")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["pending_claims"] == []


async def test_quarantine_with_items(inject_fakes, client):
    store: FakeStore = inject_fakes
    await store.list_push(Keys.PENDING_CLAIMS, {"claim_id": "q1", "reason": "low confidence"})
    async with client as c:
        resp = await c.get("/claims/quarantine")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1


async def test_validate_emits_events(inject_fakes):
    """Real QuorumPipeline (with fake validators) must emit claim_submitted + consensus_reached."""
    from quorum.pipeline import QuorumPipeline
    from quorum.contracts.config import Settings

    store: FakeStore = inject_fakes
    bus = FakeEventBus()
    set_event_bus(bus)

    settings = Settings(
        redis_url="redis://localhost",
        anthropic_api_key="",
        sentry_dsn="",
        arize_api_key="",
        arize_space_key="",
        browserbase_api_key="",
        browserbase_project_id="",
        openweather_api_key="",
        pubmed_api_key="",
        consensus_accept_threshold=0.70,
        consensus_reject_threshold=0.30,
    )
    real_pipeline = QuorumPipeline(
        validators=[FakeValidator(validator_name="v1")],
        store=store,
        event_bus=bus,
        settings=settings,
    )
    set_pipeline(real_pipeline)

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    async with client as c:
        await c.post(
            "/claims/validate",
            json={"agent_id": "a1", "workflow_id": "wf1", "statement": "test"},
        )
    event_types = [e["event_type"] for e in bus.events]
    assert "claim_submitted" in event_types
    assert "consensus_reached" in event_types


async def test_validators_reliability_empty(client):
    async with client as c:
        resp = await c.get("/validators/reliability")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_workflow_state(inject_fakes, client):
    async with client as c:
        resp = await c.get("/workflows/wf-test-001/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_id"] == "wf-test-001"
    assert "accepted_claims" in data
    assert "pending_claims" in data


async def test_consensus_recent_endpoint_empty(client):
    async with client as c:
        resp = await c.get("/consensus/recent")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_consensus_recent_endpoint_with_data(inject_fakes, client):
    store: FakeStore = inject_fakes
    await store.list_push(Keys.CONSENSUS_HISTORY, {"claim_id": "c1", "verdict": "accepted", "score": 0.9})
    async with client as c:
        resp = await c.get("/consensus/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["claim_id"] == "c1"


async def test_provenance_list_endpoint_empty(client):
    async with client as c:
        resp = await c.get("/claims/provenance")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_provenance_list_endpoint_with_data(inject_fakes, client):
    store: FakeStore = inject_fakes
    await store.set_json(
        Keys.provenance("claim-abc"),
        {"claim_id": "claim-abc", "final_verdict": "accepted", "recorded_at": "2026-06-21T00:00:00Z"},
    )
    async with client as c:
        resp = await c.get("/claims/provenance")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["claim_id"] == "claim-abc" for r in data)


async def test_quarantine_reason_is_string(inject_fakes, client):
    """Regression: quarantine entry 'reason' must be a string, not an object repr."""
    from quorum.pipeline import QuorumPipeline
    from quorum.fakes import FakeEventBus, always_review
    from quorum.contracts.config import Settings

    store: FakeStore = inject_fakes
    settings = Settings(
        redis_url="redis://localhost",
        anthropic_api_key="",
        sentry_dsn="",
        arize_api_key="",
        arize_space_key="",
        browserbase_api_key="",
        browserbase_project_id="",
        openweather_api_key="",
        pubmed_api_key="",
        consensus_accept_threshold=0.99,
        consensus_reject_threshold=0.01,
    )
    bus = FakeEventBus()
    pipeline = QuorumPipeline(validators=[always_review()], store=store, event_bus=bus, settings=settings)
    claim = make_claim(workflow_id="wf-quar-001")
    result = await pipeline.process(claim)

    assert result.verdict.value == "needs_review"
    quarantined = await store.list_all(Keys.PENDING_CLAIMS)
    assert len(quarantined) == 1
    entry = quarantined[0]
    assert isinstance(entry["reason"], str), "reason must be a str, not a ConsensusResult object"
    assert len(entry["reason"]) > 0
