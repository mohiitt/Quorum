"""Tests verifying fakes correctly implement their interfaces."""

import pytest

from quorum.contracts.interfaces import BaseStore, BaseValidator, LLMClient, ValidationPipeline
from quorum.contracts.models import Verdict
from quorum.fakes import (
    FakeEventBus,
    FakeLLMClient,
    FakePipeline,
    FakeStore,
    FakeValidator,
    always_accept,
    always_reject,
    always_review,
    make_claim,
    make_workflow_context,
)
from quorum.contracts.redis_keys import Keys


class TestFakeStore:
    @pytest.fixture
    def store(self):
        return FakeStore()

    async def test_set_get_json(self, store):
        await store.set_json("k1", {"hello": "world"})
        result = await store.get_json("k1")
        assert result == {"hello": "world"}

    async def test_get_missing_key(self, store):
        assert await store.get_json("missing") is None

    async def test_delete(self, store):
        await store.set_json("k", "v")
        await store.delete("k")
        assert await store.get_json("k") is None

    async def test_list_operations(self, store):
        await store.list_push("mylist", {"a": 1})
        await store.list_push("mylist", {"b": 2})
        items = await store.list_all("mylist")
        assert len(items) == 2
        assert items[0] == {"a": 1}

    async def test_list_remove(self, store):
        await store.list_push("mylist", "item1")
        await store.list_push("mylist", "item2")
        await store.list_remove("mylist", "item1")
        items = await store.list_all("mylist")
        assert items == ["item2"]

    async def test_keys_matching(self, store):
        await store.set_json("quorum:trust:agent1", {"score": 0.8})
        await store.set_json("quorum:trust:agent2", {"score": 0.6})
        await store.set_json("quorum:provenance:c1", {})
        keys = await store.keys_matching("quorum:trust:*")
        assert len(keys) == 2

    async def test_list_trim(self, store):
        for i in range(8):
            await store.list_push("trimlist", i)
        await store.list_trim("trimlist", 0, 2)
        items = await store.list_all("trimlist")
        assert items == [0, 1, 2]

    async def test_list_trim_missing_key_noop(self, store):
        await store.list_trim("no-such-key", 0, 5)

    def test_implements_base_store(self, store):
        assert isinstance(store, BaseStore)


class TestFakeValidator:
    async def test_always_accept(self):
        claim = make_claim()
        ctx = make_workflow_context()
        v = always_accept()
        result = await v.validate(claim, ctx)
        assert result.verdict == Verdict.ACCEPTED

    async def test_always_reject(self):
        claim = make_claim()
        ctx = make_workflow_context()
        v = always_reject()
        result = await v.validate(claim, ctx)
        assert result.verdict == Verdict.REJECTED

    async def test_always_review(self):
        claim = make_claim()
        ctx = make_workflow_context()
        v = always_review()
        result = await v.validate(claim, ctx)
        assert result.verdict == Verdict.NEEDS_REVIEW

    def test_implements_base_validator(self):
        assert isinstance(always_accept(), BaseValidator)


class TestFakeLLMClient:
    async def test_returns_preset_response(self):
        llm = FakeLLMClient(response="hello")
        result = await llm.complete("system", "user")
        assert result == "hello"

    async def test_records_calls(self):
        llm = FakeLLMClient()
        await llm.complete("sys", "msg1")
        await llm.complete("sys", "msg2")
        assert len(llm.calls) == 2

    def test_implements_llm_client(self):
        assert isinstance(FakeLLMClient(), LLMClient)


class TestFakePipeline:
    async def test_returns_consensus_result(self):
        claim = make_claim()
        pipeline = FakePipeline(verdict=Verdict.REJECTED, score=0.2)
        result = await pipeline.process(claim)
        assert result.verdict == Verdict.REJECTED
        assert result.claim_id == claim.id

    async def test_records_processed_claims(self):
        pipeline = FakePipeline()
        c1 = make_claim(claim_id="c1")
        c2 = make_claim(claim_id="c2")
        await pipeline.process(c1)
        await pipeline.process(c2)
        assert len(pipeline.processed) == 2


class TestRedisKeys:
    def test_workflow_state_key(self):
        assert Keys.workflow_state("wf1") == "quorum:state:wf1"

    def test_provenance_key(self):
        assert Keys.provenance("claim-123") == "quorum:provenance:claim-123"

    def test_trust_key(self):
        assert Keys.trust("agent-abc") == "quorum:trust:agent-abc"

    def test_reliability_key(self):
        assert Keys.reliability("source") == "quorum:reliability:source"

    def test_pending_claims_constant(self):
        assert Keys.PENDING_CLAIMS == "quorum:pending_claims"
