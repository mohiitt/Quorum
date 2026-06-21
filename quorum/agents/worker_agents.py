"""Weather demo worker agents for the Quorum validation network.

Agents:
- WeatherAgent  — periodically submits a weather forecast claim to Quorum.
- FallbackAgent — resubmits a corrected claim when the original is rejected.
- PlannerAgent  — acts on accepted forecasts (e.g. schedules an outdoor event).
- BudgetAgent   — placeholder for budget-related decisions (Phase 9+).
"""

from __future__ import annotations

import logging

from uagents import Agent, Context

from quorum.agents.protocols import (
    ClaimSubmission,
    FallbackRequest,
    FallbackResponse,
    ValidationVerdict,
)
from quorum.contracts.models import Claim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared claim factories
# ---------------------------------------------------------------------------

_BAD_CLAIM_STATEMENT = "There is a 0% chance of rain tomorrow."
_GOOD_CLAIM_STATEMENT = "There is a 75% chance of rain tomorrow based on NOAA data."


def _make_claim_dict(agent_id: str, workflow_id: str, statement: str) -> dict:
    claim = Claim(
        agent_id=agent_id,
        workflow_id=workflow_id,
        statement=statement,
    )
    return claim.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Weather Agent
# ---------------------------------------------------------------------------


def create_weather_agent(
    quorum_address: str,
    seed: str = "weather_agent_seed",
    *,
    port: int = 8002,
    submit_interval: int = 10,
    fallback_address: str | None = None,
) -> Agent:
    """Creates a weather agent that submits a (bad) rain forecast to Quorum.

    On rejection the agent sends a FallbackRequest to the fallback agent so
    that a corrected claim can be resubmitted.  ``fallback_address`` may be
    set after creation by writing to ``agent.storage`` or passed directly.
    """
    agent = Agent(name="weather-agent", seed=seed, port=port)

    _fallback_addr: list[str] = [fallback_address or ""]

    @agent.on_interval(period=submit_interval)
    async def submit_forecast(ctx: Context) -> None:
        claim_dict = _make_claim_dict(
            agent_id=ctx.address,
            workflow_id="wf-weather-demo",
            statement=_BAD_CLAIM_STATEMENT,
        )
        msg = ClaimSubmission(claim=claim_dict, workflow_id="wf-weather-demo")
        logger.info("[weather] submitting claim to quorum: %s", _BAD_CLAIM_STATEMENT)
        await ctx.send(quorum_address, msg)

    @agent.on_message(model=ValidationVerdict)
    async def handle_verdict(ctx: Context, sender: str, msg: ValidationVerdict) -> None:
        logger.info(
            "[weather] verdict for claim %s: %s (score=%.2f)",
            msg.claim_id,
            msg.verdict,
            msg.score,
        )
        if msg.verdict == "rejected":
            fb_address = _fallback_addr[0] or ctx.storage.get("fallback_address") or ""
            if fb_address:
                fb_req = FallbackRequest(
                    original_claim_id=msg.claim_id,
                    workflow_id="wf-weather-demo",
                    failure_reason=msg.rationale,
                )
                logger.info("[weather] sending fallback request for claim %s", msg.claim_id)
                await ctx.send(fb_address, fb_req)
            else:
                logger.warning("[weather] claim rejected but no fallback_address configured")

    return agent


# ---------------------------------------------------------------------------
# Fallback Agent
# ---------------------------------------------------------------------------


def create_fallback_agent(
    quorum_address: str,
    seed: str = "fallback_agent_seed",
    *,
    port: int = 8004,
) -> Agent:
    """Creates a fallback agent that submits a corrected weather claim to Quorum."""
    agent = Agent(name="fallback-agent", seed=seed, port=port)

    @agent.on_message(model=FallbackRequest)
    async def handle_fallback_request(ctx: Context, sender: str, msg: FallbackRequest) -> None:
        logger.info(
            "[fallback] received fallback request for original claim %s — resubmitting corrected claim",
            msg.original_claim_id,
        )
        corrected_dict = _make_claim_dict(
            agent_id=ctx.address,
            workflow_id=msg.workflow_id,
            statement=_GOOD_CLAIM_STATEMENT,
        )
        submission = ClaimSubmission(claim=corrected_dict, workflow_id=msg.workflow_id)
        await ctx.send(quorum_address, submission)

    @agent.on_message(model=ValidationVerdict)
    async def handle_verdict(ctx: Context, sender: str, msg: ValidationVerdict) -> None:
        logger.info(
            "[fallback] corrected claim %s verdict: %s (score=%.2f) — correction %s",
            msg.claim_id,
            msg.verdict,
            msg.score,
            "accepted ✓" if msg.verdict == "accepted" else "still rejected",
        )

    return agent


# ---------------------------------------------------------------------------
# Planner Agent
# ---------------------------------------------------------------------------


def create_planner_agent(
    seed: str = "planner_agent_seed",
    *,
    port: int = 8003,
) -> Agent:
    """Creates a planner agent that acts on accepted forecasts."""
    agent = Agent(name="planner-agent", seed=seed, port=port)

    @agent.on_message(model=ValidationVerdict)
    async def handle_verdict(ctx: Context, sender: str, msg: ValidationVerdict) -> None:
        if msg.verdict == "accepted":
            logger.info(
                "[planner] Planning outdoor event based on validated forecast (claim %s, score=%.2f).",
                msg.claim_id,
                msg.score,
            )
        else:
            logger.info(
                "[planner] Skipping planning — forecast claim %s not accepted (verdict=%s).",
                msg.claim_id,
                msg.verdict,
            )

    return agent


# ---------------------------------------------------------------------------
# Budget Agent  (placeholder for Phase 9)
# ---------------------------------------------------------------------------


def create_budget_agent(
    seed: str = "budget_agent_seed",
    *,
    port: int = 8005,
) -> Agent:
    """Creates a budget agent (placeholder — full logic arrives in Phase 9)."""
    agent = Agent(name="budget-agent", seed=seed, port=port)

    @agent.on_message(model=ValidationVerdict)
    async def handle_verdict(ctx: Context, sender: str, msg: ValidationVerdict) -> None:
        if msg.verdict == "accepted":
            logger.info(
                "[budget] Allocating budget for validated forecast (claim %s).",
                msg.claim_id,
            )

    return agent
