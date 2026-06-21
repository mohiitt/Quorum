"""Provenance store: records and retrieves immutable audit records per claim."""

from __future__ import annotations

from quorum.contracts.interfaces import BaseStore
from quorum.contracts.models import Claim, ConsensusResult, ProvenanceRecord
from quorum.contracts.redis_keys import Keys


class ProvenanceStore:
    """Persists and retrieves ProvenanceRecord objects via a BaseStore."""

    def __init__(self, store: BaseStore) -> None:
        self._store = store

    async def record(self, claim: Claim, consensus_result: ConsensusResult) -> ProvenanceRecord:
        """Build and persist a ProvenanceRecord for the given claim/result pair."""
        provenance = ProvenanceRecord(
            claim_id=claim.id,
            claim=claim,
            consensus_result=consensus_result,
            validator_names=[str(vr.validator_name) for vr in consensus_result.validator_results],
            final_verdict=consensus_result.verdict,
            confidence_score=consensus_result.score,
        )
        await self._store.set_json(
            Keys.provenance(claim.id),
            provenance.model_dump(mode="json"),
        )
        return provenance

    async def get(self, claim_id: str) -> ProvenanceRecord | None:
        """Retrieve the ProvenanceRecord for a claim, or None if not found."""
        data = await self._store.get_json(Keys.provenance(claim_id))
        if data is None:
            return None
        return ProvenanceRecord.model_validate(data)

    async def list_for_workflow(self, workflow_id: str) -> list[ProvenanceRecord]:
        """Return all ProvenanceRecords whose claim belongs to the given workflow."""
        keys = await self._store.keys_matching("quorum:provenance:*")
        records: list[ProvenanceRecord] = []
        for key in keys:
            data = await self._store.get_json(key)
            if data is None:
                continue
            pr = ProvenanceRecord.model_validate(data)
            if pr.claim.workflow_id == workflow_id:
                records.append(pr)
        return records
