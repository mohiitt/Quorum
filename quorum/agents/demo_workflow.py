"""
Quorum weather-forecast demo workflow.

Run with:
    python -m quorum.agents.demo_workflow

What happens:
1. Weather Agent submits a bad claim  ("0% chance of rain tomorrow")
2. Quorum validates it via the real pipeline → REJECTED (contradicts OWM + reasoning)
3. Weather Agent forwards a FallbackRequest to the Fallback Agent
4. Fallback Agent resubmits a corrected claim ("75% rain based on NOAA data")
5. Quorum validates the corrected claim → ACCEPTED
6. Planner Agent and Budget Agent act on the validated forecast

Validators loaded:
- SourceValidator  (OpenWeatherMap, PubMed, Browserbase — gracefully skipped if keys missing)
- ConsistencyValidator (Anthropic Claude — skipped if ANTHROPIC_API_KEY missing)
- ReasoningValidator   (Anthropic Claude — skipped if ANTHROPIC_API_KEY missing)

Set API keys in .env before running for real validation.  Without keys the
pipeline falls back to a single FakeValidator so the Bureau flow still works.
"""

from __future__ import annotations

import logging

from uagents import Bureau

from quorum.agents.quorum_agent import create_quorum_agent
from quorum.agents.worker_agents import (
    create_budget_agent,
    create_fallback_agent,
    create_planner_agent,
    create_weather_agent,
)

logging.basicConfig(level=logging.INFO)


def _build_real_pipeline():
    """Build a real QuorumPipeline using whatever validators are configured."""
    from quorum.api.event_bus import InMemoryEventBus
    from quorum.contracts.config import get_settings
    from quorum.fakes import FakeStore, always_accept
    from quorum.pipeline import QuorumPipeline

    settings = get_settings()
    store = FakeStore()
    bus = InMemoryEventBus()
    validators: list = []

    try:
        from quorum.validators.source import BrowserbaseHTTPClient, SourceValidator
        bb_client = None
        if settings.browserbase_api_key and settings.browserbase_api_key.strip("."):
            if settings.browserbase_project_id and settings.browserbase_project_id.strip("."):
                bb_client = BrowserbaseHTTPClient(
                    api_key=settings.browserbase_api_key,
                    project_id=settings.browserbase_project_id,
                )
        validators.append(SourceValidator(settings=settings, browserbase_client=bb_client))
    except Exception as exc:
        logging.getLogger(__name__).warning("Source validator unavailable: %s", exc)

    if settings.anthropic_api_key and settings.anthropic_api_key.strip("."):
        try:
            from quorum.validators.consistency import AnthropicLLMClient, ConsistencyValidator
            validators.append(ConsistencyValidator(llm_client=AnthropicLLMClient(settings.anthropic_api_key)))
        except Exception as exc:
            logging.getLogger(__name__).warning("Consistency validator unavailable: %s", exc)

        try:
            from quorum.validators.consistency import AnthropicLLMClient as RLLM
            from quorum.validators.reasoning import ReasoningValidator
            validators.append(ReasoningValidator(llm_client=RLLM(settings.anthropic_api_key)))
        except Exception as exc:
            logging.getLogger(__name__).warning("Reasoning validator unavailable: %s", exc)

    if not validators:
        logging.getLogger(__name__).warning("No validators loaded — using FakeValidator fallback")
        validators = [always_accept("fallback")]

    return QuorumPipeline(validators=validators, store=store, event_bus=bus, settings=settings)


def run_demo() -> None:
    """Bootstrap all agents into a Bureau and start the event loop."""
    pipeline = _build_real_pipeline()

    quorum = create_quorum_agent(pipeline)

    fallback = create_fallback_agent(quorum_address=quorum.address)
    weather = create_weather_agent(
        quorum_address=quorum.address,
        fallback_address=fallback.address,
    )
    planner = create_planner_agent()
    budget = create_budget_agent()

    bureau = Bureau()
    bureau.add(quorum)
    bureau.add(weather)
    bureau.add(planner)
    bureau.add(fallback)
    bureau.add(budget)

    bureau.run()


if __name__ == "__main__":
    run_demo()
