"""FastAPI router implementing all REST endpoints defined in docs/api.md."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from quorum.api.dependencies import get_event_bus, get_pipeline, get_store
from quorum.api.observability import log_validator_result_to_arize
from quorum.contracts.interfaces import BaseStore, EventBus, ValidationPipeline
from quorum.contracts.models import (
    Claim,
    ProvenanceRecord,
    TrustScore,
    ValidationResponse,
    ValidatorReliability,
    WorkflowStateResponse,
)
from quorum.contracts.redis_keys import Keys

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class ValidateClaimRequest(BaseModel):
    agent_id: str
    workflow_id: str
    statement: str
    payload: dict[str, Any] = {}


class QuarantineResponse(BaseModel):
    pending_claims: list[dict]
    count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@router.post("/claims/validate", response_model=ValidationResponse)
async def validate_claim(
    body: ValidateClaimRequest,
    pipeline: ValidationPipeline = Depends(get_pipeline),
) -> ValidationResponse:
    claim = Claim(
        agent_id=body.agent_id,
        workflow_id=body.workflow_id,
        statement=body.statement,
        payload=body.payload,
    )

    result = await pipeline.process(claim)

    # Log each validator result to Arize
    for vr in result.validator_results:
        log_validator_result_to_arize(
            validator_name=str(vr.validator_name),
            verdict=vr.verdict.value,
            confidence=vr.confidence,
            claim_id=claim.id,
        )

    quarantined = result.verdict.value == "needs_review"

    return ValidationResponse(
        claim_id=result.claim_id,
        verdict=result.verdict,
        score=result.score,
        rationale=result.rationale,
        quarantined=quarantined,
        provenance_url=f"/claims/{result.claim_id}/provenance",
    )


@router.get("/claims/quarantine", response_model=QuarantineResponse)
async def list_quarantine(
    store: BaseStore = Depends(get_store),
) -> QuarantineResponse:
    items = await store.list_all(Keys.PENDING_CLAIMS)
    return QuarantineResponse(pending_claims=items, count=len(items))


@router.get("/claims/{claim_id}/provenance")
async def get_provenance(
    claim_id: str,
    store: BaseStore = Depends(get_store),
) -> dict:
    data = await store.get_json(Keys.provenance(claim_id))
    if data is None:
        raise HTTPException(status_code=404, detail=f"Provenance not found for claim {claim_id}")
    return data


@router.get("/workflows/{workflow_id}/state", response_model=WorkflowStateResponse)
async def get_workflow_state(
    workflow_id: str,
    store: BaseStore = Depends(get_store),
) -> WorkflowStateResponse:
    # Accepted claim IDs
    claim_ids: list[str] = await store.list_all(Keys.workflow_state(workflow_id))

    accepted: list[Claim] = []
    for cid in claim_ids:
        raw = await store.get_json(Keys.workflow_claim(workflow_id, cid))
        if raw:
            try:
                accepted.append(Claim.model_validate(raw))
            except Exception:
                pass

    # Pending claims for this workflow
    all_pending = await store.list_all(Keys.PENDING_CLAIMS)
    pending: list[Claim] = []
    for item in all_pending:
        try:
            claim_data = item.get("claim") if isinstance(item, dict) else item
            c = Claim.model_validate(claim_data)
            if c.workflow_id == workflow_id:
                pending.append(c)
        except Exception:
            pass

    # Trust scores
    trust_keys = await store.keys_matching(Keys.TRUST_ALL_PATTERN)
    trust_scores: list[TrustScore] = []
    for key in trust_keys:
        raw = await store.get_json(key)
        if raw:
            try:
                trust_scores.append(TrustScore.model_validate(raw))
            except Exception:
                pass

    return WorkflowStateResponse(
        workflow_id=workflow_id,
        accepted_claims=accepted,
        pending_claims=pending,
        agent_trust_scores=trust_scores,
    )


@router.get("/agents/trust")
async def get_agent_trust(
    store: BaseStore = Depends(get_store),
) -> list[dict]:
    keys = await store.keys_matching(Keys.TRUST_ALL_PATTERN)
    scores = []
    for key in keys:
        raw = await store.get_json(key)
        if raw:
            scores.append(raw)
    return scores


@router.get("/validators/reliability")
async def get_validator_reliability(
    store: BaseStore = Depends(get_store),
) -> list[dict]:
    keys = await store.keys_matching(Keys.RELIABILITY_ALL_PATTERN)
    reliabilities = []
    for key in keys:
        raw = await store.get_json(key)
        if raw:
            reliabilities.append(raw)
    return reliabilities


@router.get("/consensus/recent")
async def get_recent_consensus(
    store: BaseStore = Depends(get_store),
) -> list[dict]:
    items = await store.list_all(Keys.CONSENSUS_HISTORY)
    return list(reversed(items))


@router.get("/claims/provenance")
async def list_provenance(
    store: BaseStore = Depends(get_store),
) -> list[dict]:
    keys = await store.keys_matching("quorum:provenance:*")
    records = []
    for key in keys:
        raw = await store.get_json(key)
        if raw:
            records.append(raw)
    records.sort(key=lambda r: r.get("recorded_at", ""), reverse=True)
    return records[:50]
