"""Tests for quorum.agents.quorum_agent factory."""

import pytest

uagents = pytest.importorskip("uagents")

from uagents import Agent  # noqa: E402

from quorum.agents.quorum_agent import create_quorum_agent  # noqa: E402
from quorum.fakes import FakePipeline  # noqa: E402


class TestCreateQuorumAgent:
    def test_returns_agent_instance(self):
        agent = create_quorum_agent(FakePipeline())
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        agent = create_quorum_agent(FakePipeline(), name="my-gatekeeper")
        assert agent.name == "my-gatekeeper"

    def test_default_agent_name(self):
        agent = create_quorum_agent(FakePipeline())
        assert agent.name == "quorum-gatekeeper"

    def test_agent_has_deterministic_address(self):
        a1 = create_quorum_agent(FakePipeline(), seed="seed-abc")
        a2 = create_quorum_agent(FakePipeline(), seed="seed-abc")
        assert a1.address == a2.address

    def test_different_seeds_produce_different_addresses(self):
        a1 = create_quorum_agent(FakePipeline(), seed="seed-one")
        a2 = create_quorum_agent(FakePipeline(), seed="seed-two")
        assert a1.address != a2.address

    def test_quorum_protocol_included(self):
        from quorum.agents.protocols import quorum_protocol

        agent = create_quorum_agent(FakePipeline())
        # uAgents tracks included protocols by digest; the protocol's digest
        # should appear in the agent's protocol digest set.
        included_digests = set(agent.protocols.keys())
        assert quorum_protocol.digest in included_digests

    def test_accepts_custom_port(self):
        agent = create_quorum_agent(FakePipeline(), port=9999)
        assert isinstance(agent, Agent)

    def test_pipeline_is_injected_not_instantiated(self):
        pipeline = FakePipeline()
        create_quorum_agent(pipeline)
        # FakePipeline.processed starts empty — no process() call at construction.
        assert pipeline.processed == []
