"""Tests for quorum.agents.worker_agents factory functions."""

import pytest

uagents = pytest.importorskip("uagents")

from uagents import Agent  # noqa: E402

from quorum.agents.worker_agents import (  # noqa: E402
    create_budget_agent,
    create_fallback_agent,
    create_planner_agent,
    create_weather_agent,
)

# A placeholder address used when a quorum address is required by the factory.
_DUMMY_QUORUM_ADDRESS = "agent1qfakeaddress000000000000000000000000000000000000000000000000"


class TestCreateWeatherAgent:
    def test_returns_agent_instance(self):
        agent = create_weather_agent(quorum_address=_DUMMY_QUORUM_ADDRESS)
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        agent = create_weather_agent(quorum_address=_DUMMY_QUORUM_ADDRESS)
        assert agent.name == "weather-agent"

    def test_deterministic_address(self):
        a1 = create_weather_agent(_DUMMY_QUORUM_ADDRESS, seed="w-seed")
        a2 = create_weather_agent(_DUMMY_QUORUM_ADDRESS, seed="w-seed")
        assert a1.address == a2.address


class TestCreateFallbackAgent:
    def test_returns_agent_instance(self):
        agent = create_fallback_agent(quorum_address=_DUMMY_QUORUM_ADDRESS)
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        agent = create_fallback_agent(quorum_address=_DUMMY_QUORUM_ADDRESS)
        assert agent.name == "fallback-agent"

    def test_deterministic_address(self):
        a1 = create_fallback_agent(_DUMMY_QUORUM_ADDRESS, seed="f-seed")
        a2 = create_fallback_agent(_DUMMY_QUORUM_ADDRESS, seed="f-seed")
        assert a1.address == a2.address


class TestCreatePlannerAgent:
    def test_returns_agent_instance(self):
        agent = create_planner_agent()
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        agent = create_planner_agent()
        assert agent.name == "planner-agent"

    def test_deterministic_address(self):
        a1 = create_planner_agent(seed="p-seed")
        a2 = create_planner_agent(seed="p-seed")
        assert a1.address == a2.address


class TestCreateBudgetAgent:
    def test_returns_agent_instance(self):
        agent = create_budget_agent()
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        agent = create_budget_agent()
        assert agent.name == "budget-agent"

    def test_deterministic_address(self):
        a1 = create_budget_agent(seed="b-seed")
        a2 = create_budget_agent(seed="b-seed")
        assert a1.address == a2.address


class TestAllAgentFactories:
    def test_all_four_return_agent_instances(self):
        agents = [
            create_weather_agent(_DUMMY_QUORUM_ADDRESS),
            create_fallback_agent(_DUMMY_QUORUM_ADDRESS),
            create_planner_agent(),
            create_budget_agent(),
        ]
        assert len(agents) == 4
        for agent in agents:
            assert isinstance(agent, Agent)

    def test_all_have_distinct_names(self):
        agents = [
            create_weather_agent(_DUMMY_QUORUM_ADDRESS),
            create_fallback_agent(_DUMMY_QUORUM_ADDRESS),
            create_planner_agent(),
            create_budget_agent(),
        ]
        names = [a.name for a in agents]
        assert len(names) == len(set(names)), "All agent names should be unique"
