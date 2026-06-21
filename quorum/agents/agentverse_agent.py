"""Quorum Validator — Agentverse-publishable trust & consensus agent.

Accepts two kinds of messages:
  1. ClaimSubmission  — structured agent-to-agent call (uAgents protocol)
  2. TextValidationRequest — plain-text query for ASI:One chat interface

Builds a self-contained QuorumPipeline (no FastAPI, no Redis required).
When AGENTVERSE_API_KEY is set the agent registers on Agentverse and
becomes reachable from any uAgent or ASI:One.
"""

from __future__ import annotations

import logging
import os

from uagents import Agent, Context, Model

from quorum.agents.protocols import ClaimSubmission, ValidationVerdict, quorum_protocol
from quorum.contracts.models import Claim

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Additional message models (not in protocols.py so we don't touch main code)
# ---------------------------------------------------------------------------


class TextValidationRequest(Model):
    """Plain-text validation request — usable from ASI:One chat."""

    statement: str
    agent_id: str = "asi-one-user"
    workflow_id: str = "wf-agentverse"


class TextValidationResponse(Model):
    """Rich validation response returned to ASI:One or any calling agent."""

    verdict: str          # "accepted" | "rejected" | "needs_review"
    score: float          # 0–1 consensus score
    rationale: str
    validator_breakdown: list[dict]  # per-validator details


# ---------------------------------------------------------------------------
# Pipeline bootstrap (no FastAPI, no Redis required)
# ---------------------------------------------------------------------------


async def _build_pipeline():
    """Return a self-contained QuorumPipeline using in-memory state.

    Mirrors startup.py logic but returns the pipeline directly rather than
    injecting it into FastAPI's dependency container.
    """
    from quorum.contracts.config import get_settings
    from quorum.fakes import FakeStore
    from quorum.fakes.event_bus import FakeEventBus
    from quorum.pipeline import QuorumPipeline

    settings = get_settings()
    store = FakeStore()
    bus = FakeEventBus()          # no WS clients to push to

    validators: list = []

    # Source validator (web search — works without extra keys)
    try:
        from quorum.validators.source import BrowserbaseHTTPClient, SourceValidator

        bb_client = None
        if (
            settings.browserbase_api_key
            and settings.browserbase_api_key.strip(".")
            and settings.browserbase_project_id
            and settings.browserbase_project_id.strip(".")
        ):
            bb_client = BrowserbaseHTTPClient(
                api_key=settings.browserbase_api_key,
                project_id=settings.browserbase_project_id,
            )
            logger.info("[agentverse] Browserbase enabled")
        validators.append(SourceValidator(settings=settings, browserbase_client=bb_client))
        logger.info("[agentverse] SourceValidator loaded")
    except Exception as exc:
        logger.warning("[agentverse] SourceValidator unavailable: %s", exc)

    # Consistency + Reasoning validators (require Anthropic key)
    if settings.anthropic_api_key and settings.anthropic_api_key.strip("."):
        try:
            from quorum.validators.consistency import (
                AnthropicLLMClient,
                ConsistencyValidator,
            )

            validators.append(
                ConsistencyValidator(llm_client=AnthropicLLMClient(settings.anthropic_api_key))
            )
            logger.info("[agentverse] ConsistencyValidator loaded")
        except Exception as exc:
            logger.warning("[agentverse] ConsistencyValidator unavailable: %s", exc)

        try:
            from quorum.validators.consistency import AnthropicLLMClient as _LLM
            from quorum.validators.reasoning import ReasoningValidator

            validators.append(ReasoningValidator(llm_client=_LLM(settings.anthropic_api_key)))
            logger.info("[agentverse] ReasoningValidator loaded")
        except Exception as exc:
            logger.warning("[agentverse] ReasoningValidator unavailable: %s", exc)

    if not validators:
        logger.warning("[agentverse] No validators loaded — using FakeValidator (accept-all)")
        from quorum.fakes import always_accept

        validators = [always_accept("fallback")]

    pipeline = QuorumPipeline(
        validators=validators,
        store=store,
        event_bus=bus,
        settings=settings,
    )
    logger.info(
        "[agentverse] Pipeline ready — %d validator(s): %s",
        len(validators),
        ", ".join(getattr(v, "name", type(v).__name__) for v in validators),
    )
    return pipeline


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def _format_breakdown(validator_results) -> list[dict]:
    return [
        {
            "validator": str(vr.validator_name).replace("ValidatorName.", ""),
            "verdict": vr.verdict.value,
            "confidence": round(vr.confidence, 3),
            "rationale": (vr.rationale or "")[:300],
        }
        for vr in validator_results
    ]


def create_agentverse_agent(
    *,
    name: str = "quorum-validator",
    seed: str | None = None,
    port: int = 8001,
    mailbox: bool = True,
) -> Agent:
    """Create the Agentverse-publishable Quorum validation agent.

    Args:
        name:    Human-readable agent name shown in the marketplace.
        seed:    Deterministic seed for a stable agent address. Set via
                 AGENT_SEED env var so the address never changes between
                 deploys.
        mailbox: When True the agent registers on Agentverse (requires
                 AGENTVERSE_API_KEY).  Set to False for local-only testing.
    """
    _seed = seed or os.getenv("AGENT_SEED", "quorum_agentverse_seed_v1")

    agent = Agent(
        name=name,
        seed=_seed,
        port=port,
        mailbox=mailbox,
    )

    # Lazily-initialised pipeline — built on first use inside the async loop.
    _pipeline_ref: list = [None]

    async def _get_pipeline():
        if _pipeline_ref[0] is None:
            _pipeline_ref[0] = await _build_pipeline()
        return _pipeline_ref[0]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @agent.on_event("startup")
    async def on_startup(ctx: Context) -> None:
        logger.info("[agentverse] Quorum validator online — address: %s", ctx.address)
        await _get_pipeline()  # warm-up: load models, open HTTP clients

    # ------------------------------------------------------------------
    # Handler 1: structured ClaimSubmission (agent-to-agent protocol)
    # ------------------------------------------------------------------

    @quorum_protocol.on_message(model=ClaimSubmission, replies={ValidationVerdict})
    async def handle_claim_submission(
        ctx: Context, sender: str, msg: ClaimSubmission
    ) -> None:
        """Validate a claim submitted by another uAgent."""
        pipeline = await _get_pipeline()

        try:
            claim = Claim(**msg.claim)
        except Exception as exc:
            logger.warning("[agentverse] Malformed ClaimSubmission from %s: %s", sender, exc)
            return

        logger.info("[agentverse] ClaimSubmission from %s — '%s'", sender, claim.statement[:80])
        result = await pipeline.process(claim)

        await ctx.send(
            sender,
            ValidationVerdict(
                claim_id=claim.id,
                verdict=result.verdict.value,
                score=round(result.score, 4),
                rationale=result.rationale,
                quarantined=(result.verdict.value == "needs_review"),
            ),
        )

    # ------------------------------------------------------------------
    # Handler 2: plain-text TextValidationRequest (ASI:One chat)
    # ------------------------------------------------------------------

    @agent.on_message(model=TextValidationRequest, replies={TextValidationResponse})
    async def handle_text_request(
        ctx: Context, sender: str, msg: TextValidationRequest
    ) -> None:
        """Validate a plain-text statement — called from ASI:One chat interface."""
        pipeline = await _get_pipeline()

        claim = Claim(
            agent_id=msg.agent_id,
            workflow_id=msg.workflow_id,
            statement=msg.statement,
        )
        logger.info("[agentverse] TextValidationRequest from %s — '%s'", sender, msg.statement[:80])
        result = await pipeline.process(claim)

        await ctx.send(
            sender,
            TextValidationResponse(
                verdict=result.verdict.value,
                score=round(result.score, 4),
                rationale=result.rationale,
                validator_breakdown=_format_breakdown(result.validator_results),
            ),
        )

    agent.include(quorum_protocol)
    return agent
