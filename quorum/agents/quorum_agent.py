"""Quorum gatekeeper agent — validates claims via an injected pipeline."""

from __future__ import annotations

import logging

from uagents import Agent, Context

from quorum.agents.protocols import ClaimSubmission, ValidationVerdict, quorum_protocol
from quorum.contracts.interfaces import ValidationPipeline
from quorum.contracts.models import Claim

logger = logging.getLogger(__name__)


def create_quorum_agent(
    pipeline: ValidationPipeline,
    *,
    name: str = "quorum-gatekeeper",
    seed: str = "quorum_seed_phrase_001",
    port: int = 8001,
) -> Agent:
    """Factory that creates the Quorum gatekeeper agent with an injected pipeline.

    The pipeline is captured via closure so the handler remains a plain async
    function (no class needed), keeping the uAgents decorator pattern clean.
    """
    agent = Agent(
        name=name,
        seed=seed,
        port=port,
        endpoint=[f"http://localhost:{port}/submit"],
    )

    @quorum_protocol.on_message(model=ClaimSubmission, replies={ValidationVerdict})
    async def handle_claim_submission(ctx: Context, sender: str, msg: ClaimSubmission) -> None:
        claim = Claim(**msg.claim)
        logger.info("[quorum] received claim %s from %s", claim.id, sender)

        consensus_result = await pipeline.process(claim)

        quarantined = consensus_result.verdict.value == "needs_review"
        verdict_msg = ValidationVerdict(
            claim_id=claim.id,
            verdict=consensus_result.verdict.value,
            score=consensus_result.score,
            rationale=consensus_result.rationale,
            quarantined=quarantined,
        )

        logger.info(
            "[quorum] claim %s → verdict=%s score=%.2f quarantined=%s",
            claim.id,
            verdict_msg.verdict,
            verdict_msg.score,
            quarantined,
        )
        await ctx.send(sender, verdict_msg)

    agent.include(quorum_protocol)
    return agent
