"""Real ValidationPipeline — wires all validators → consensus → state/provenance/trust.

This is the integration point assembled in Phase 9.
"""

from __future__ import annotations

import asyncio
import logging

from quorum.consensus.engine import ConsensusEngine
from quorum.consensus.quarantine import Quarantine
from quorum.contracts.config import Settings, get_settings
from quorum.contracts.errors import PipelineError
from quorum.contracts.interfaces import (
    BaseStore,
    BaseValidator,
    EventBus,
    ValidationPipeline,
)
from quorum.contracts.models import (
    Claim,
    ConsensusEvent,
    ConsensusResult,
    Verdict,
    WorkflowContext,
)
from quorum.contracts.redis_keys import Keys
from quorum.state.provenance import ProvenanceStore
from quorum.state.trust import TrustManager

logger = logging.getLogger(__name__)


class QuorumPipeline(ValidationPipeline):
    """Full validation pipeline: validators → consensus → quarantine/state/provenance/trust."""

    def __init__(
        self,
        validators: list[BaseValidator],
        store: BaseStore,
        event_bus: EventBus,
        settings: Settings | None = None,
    ) -> None:
        self._validators = validators
        self._store = store
        self._event_bus = event_bus
        self._settings = settings or get_settings()
        self._engine = ConsensusEngine(self._settings)
        self._quarantine = Quarantine(store)
        self._provenance = ProvenanceStore(store)
        self._trust = TrustManager(store)

    async def process(self, claim: Claim) -> ConsensusResult:
        """Run full pipeline for a single claim."""
        try:
            return await self._run(claim)
        except Exception as exc:
            logger.error("Pipeline error for claim %s: %s", claim.id, exc)
            raise PipelineError(f"Pipeline failed for claim {claim.id}: {exc}") from exc

    async def _run(self, claim: Claim) -> ConsensusResult:
        # 1. Build workflow context — non-fatal if store is unavailable
        try:
            context = await self._build_context(claim.workflow_id)
        except Exception as exc:
            logger.warning("Context build failed, using empty context (non-fatal): %s", exc)
            context = WorkflowContext(workflow_id=claim.workflow_id, accepted_claims=[])

        # 2. Publish claim_submitted event
        await self._publish(
            ConsensusEvent(
                event_type="claim_submitted",
                claim_id=claim.id,
                workflow_id=claim.workflow_id,
                data={"agent_id": claim.agent_id, "statement": claim.statement},
            )
        )

        # 3. Run all validators concurrently
        logger.info(
            "[PIPELINE] agent=%s | claim=%.120s",
            claim.agent_id, claim.statement,
        )
        tasks = [v.validate(claim, context) for v in self._validators]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        validator_results = []
        for v, result in zip(self._validators, raw_results):
            if isinstance(result, Exception):
                logger.warning("Validator %s failed: %s", v.name, result)
            else:
                validator_results.append(result)
                from quorum.consensus.scoring import _p_true, mean_evidence_quality
                pt = _p_true(result)
                eq = mean_evidence_quality(result.evidence)
                contrib = result.reliability * pt * eq
                logger.info(
                    "[PIPELINE]   validator=%-12s verdict=%-12s conf=%.2f  "
                    "reliability=%.2f p_true=%.2f ev_qual=%.2f → contrib=%.4f",
                    v.name,
                    result.verdict.value,
                    result.confidence,
                    result.reliability,
                    pt,
                    eq,
                    contrib,
                )
                await self._publish(
                    ConsensusEvent(
                        event_type="validator_result",
                        claim_id=claim.id,
                        workflow_id=claim.workflow_id,
                        data={
                            "validator_name": v.name,
                            "verdict": result.verdict.value,
                            "confidence": result.confidence,
                        },
                    )
                )

        # 4. Run consensus
        consensus = self._engine.run(claim.id, validator_results)
        logger.info(
            "[PIPELINE]   CONSENSUS score=%.4f → %s",
            consensus.score, consensus.verdict.value,
        )

        # 5. Publish final consensus event FIRST so dashboard always gets notified
        #    even if subsequent store operations fail.
        await self._publish(
            ConsensusEvent(
                event_type="consensus_reached",
                claim_id=claim.id,
                workflow_id=claim.workflow_id,
                data={
                    "verdict": consensus.verdict.value,
                    "score": consensus.score,
                    "rationale": consensus.rationale,
                    "statement": claim.statement,
                    "agent_id": claim.agent_id,
                    "consensus_result": consensus.model_dump(mode="json"),
                },
            )
        )

        # 6. Persist provenance and push to recent consensus history — non-fatal
        try:
            await self._provenance.record(claim, consensus)
        except Exception as exc:
            logger.warning("Provenance recording failed (non-fatal): %s", exc)

        try:
            await self._store.list_push(
                Keys.CONSENSUS_HISTORY,
                {**consensus.model_dump(mode="json"), "statement": claim.statement, "agent_id": claim.agent_id},
            )
            await self._store.list_trim(
                Keys.CONSENSUS_HISTORY,
                0,
                Keys.CONSENSUS_HISTORY_MAX - 1,
            )
        except Exception as exc:
            logger.warning("Consensus history push failed (non-fatal): %s", exc)

        # 7. Update agent trust — non-fatal
        try:
            await self._trust.update_agent_trust(claim.agent_id, consensus.verdict)
        except Exception as exc:
            logger.warning("Trust update failed (non-fatal): %s", exc)

        # 8. Update validator reliabilities — non-fatal
        for vr in validator_results:
            name = str(vr.validator_name)
            correct = vr.verdict == consensus.verdict
            try:
                await self._trust.update_validator_reliability(name, correct)
            except Exception as exc:
                logger.warning("Reliability update failed for %s (non-fatal): %s", name, exc)

        # 9. Quarantine or write canonical state — non-fatal
        try:
            if consensus.verdict == Verdict.NEEDS_REVIEW:
                await self._quarantine.quarantine(claim, consensus.rationale)
                await self._publish(
                    ConsensusEvent(
                        event_type="quarantined",
                        claim_id=claim.id,
                        workflow_id=claim.workflow_id,
                        data={"reason": "score between accept and reject thresholds"},
                    )
                )
            elif consensus.verdict == Verdict.ACCEPTED:
                await self._store.list_push(Keys.workflow_state(claim.workflow_id), claim.id)
                await self._store.set_json(
                    Keys.workflow_claim(claim.workflow_id, claim.id),
                    claim.model_dump(),
                )
        except Exception as exc:
            logger.warning("State persistence failed (non-fatal): %s", exc)

        return consensus

    async def _build_context(self, workflow_id: str) -> WorkflowContext:
        """Fetch accepted claims for this workflow to give validators context."""
        from quorum.contracts.models import Claim as ClaimModel

        claim_ids: list[str] = await self._store.list_all(Keys.workflow_state(workflow_id))
        accepted: list[ClaimModel] = []
        for cid in claim_ids:
            raw = await self._store.get_json(Keys.workflow_claim(workflow_id, cid))
            if raw:
                try:
                    accepted.append(ClaimModel.model_validate(raw))
                except Exception:
                    pass
        return WorkflowContext(workflow_id=workflow_id, accepted_claims=accepted)

    async def _publish(self, event: ConsensusEvent) -> None:
        try:
            await self._event_bus.publish(event.model_dump())
        except Exception as exc:
            logger.debug("Event publish failed: %s", exc)
