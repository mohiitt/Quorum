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

from uagents import Agent, Context, Model, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

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


def _clean_name(raw) -> str:
    """Normalise validator name: strip enum prefix and lowercase."""
    return str(raw).replace("ValidatorName.", "").lower()


def _format_breakdown(validator_results) -> list[dict]:
    return [
        {
            "validator": _clean_name(vr.validator_name),
            "verdict": vr.verdict.value,
            "confidence": round(vr.confidence, 3),
            "rationale": (vr.rationale or "")[:300],
        }
        for vr in validator_results
    ]


_AGENT_DESCRIPTION = (
    "Multi-agent trust & consensus layer. Validates any claim via Source (live web), "
    "Consistency, and Reasoning validators. Returns accepted/rejected/needs_review "
    "verdict with a 0-1 confidence score and full per-validator breakdown."
)


def create_agentverse_agent(
    *,
    name: str = "Quorum Validator",
    seed: str | None = None,
    port: int = 8001,
    mailbox: bool = True,
) -> Agent:
    """Create the Agentverse-publishable Quorum validation agent.

    Args:
        name:    Display name shown in the Agentverse marketplace.
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
        description=_AGENT_DESCRIPTION,
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
    async def on_startup(ctx: Context) -> None:  # noqa: ARG001
        logger.info("[agentverse] Quorum validator online — address: %s", agent.address)
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

    # ------------------------------------------------------------------
    # Handler 3: Agent Chat Protocol — enables ASI:One chat UI
    # ------------------------------------------------------------------

    chat_protocol = Protocol(spec=chat_protocol_spec)

    @chat_protocol.on_message(ChatMessage, replies=None)
    async def handle_chat_message(
        ctx: Context, sender: str, msg: ChatMessage
    ) -> None:
        """Handle plain-text chat from ASI:One or any agent using the chat protocol."""
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

        user_text = msg.text().strip()
        if not user_text:
            await ctx.send(
                sender,
                ChatMessage(content=[TextContent(
                    text="Please send a claim or statement to validate."
                )]),
            )
            return

        pipeline = await _get_pipeline()
        claim = Claim(
            agent_id=sender,
            workflow_id="wf-agentverse-chat",
            statement=user_text,
        )
        logger.info("[agentverse] chat from %s — '%s'", sender, user_text[:80])

        try:
            result = await pipeline.process(claim)
            breakdown = _format_breakdown(result.validator_results)

            _v_emoji = {"accepted": "✅", "rejected": "❌", "needs_review": "⚠️"}
            verdict_emoji = _v_emoji.get(result.verdict.value, "❓")

            n_total     = len(breakdown)
            n_accepted  = sum(1 for b in breakdown if b["verdict"] == "accepted")
            n_rejected  = sum(1 for b in breakdown if b["verdict"] == "rejected")
            n_review    = sum(1 for b in breakdown if b["verdict"] == "needs_review")

            validator_sections = []
            for b in breakdown:
                ve = _v_emoji.get(b["verdict"], "❓")
                rationale = b["rationale"]
                short = rationale[:250] + ("…" if len(rationale) > 250 else "")
                validator_sections.append(
                    f"{ve} **{b['validator'].capitalize()}** — "
                    f"{b['verdict'].replace('_', ' ')} ({b['confidence']*100:.0f}%)\n"
                    f"{short}"
                )

            reply = "\n\n".join([
                f"{verdict_emoji} **{result.verdict.value.replace('_', ' ').upper()}**  |  score: {result.score:.2f}  |  {n_total} validators: {n_accepted} accepted · {n_rejected} rejected · {n_review} needs review",
                *validator_sections,
            ])
        except Exception as exc:
            logger.error("[agentverse] chat pipeline error: %s", exc)
            reply = "⚠️ Validation failed due to an internal error. Please try again."

        await ctx.send(sender, ChatMessage(content=[TextContent(text=reply)]))

    @chat_protocol.on_message(ChatAcknowledgement, replies=None)
    async def handle_chat_ack(
        ctx: Context, sender: str, msg: ChatAcknowledgement  # noqa: ARG001
    ) -> None:
        pass  # acknowledgements are fire-and-forget

    agent.include(chat_protocol)

    return agent
