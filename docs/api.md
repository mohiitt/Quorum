# Quorum API Schema

> **Contract document** — Phase 7 (FastAPI) implements this; Phase 8 (Dashboard) mocks against this.
> Do not diverge without updating both sides.

Base URL: `http://localhost:8000`
WebSocket: `ws://localhost:8000/stream`

---

## REST Endpoints

### POST /claims/validate

Submit a claim for validation through the Quorum pipeline.

**Request body** (`application/json`):
```json
{
  "agent_id": "agent-weather-001",
  "workflow_id": "wf-demo-001",
  "statement": "There is a 0% chance of rain tomorrow.",
  "payload": {
    "source": "weather-api",
    "confidence": 0.42
  }
}
```

**Response** `200 OK`:
```json
{
  "claim_id": "uuid-v4",
  "verdict": "rejected",
  "score": 0.21,
  "rationale": "Source validator found 87% rain probability in NOAA data. Claim contradicts external evidence.",
  "quarantined": false,
  "provenance_url": "/claims/uuid-v4/provenance"
}
```

`verdict` is one of: `"accepted"` | `"rejected"` | `"needs_review"`

---

### GET /claims/{claim_id}/provenance

Retrieve the full provenance audit record for a claim.

**Response** `200 OK`:
```json
{
  "claim_id": "uuid-v4",
  "claim": { "...": "full Claim object" },
  "consensus_result": {
    "claim_id": "uuid-v4",
    "verdict": "rejected",
    "score": 0.21,
    "validator_results": [
      {
        "validator_name": "source",
        "verdict": "rejected",
        "confidence": 0.92,
        "evidence": [
          {
            "source": "NOAA",
            "url": "https://api.weather.gov/...",
            "snippet": "87% probability of precipitation",
            "quality": 0.95
          }
        ],
        "failure_mode": "contradicts_source",
        "reliability": 0.88,
        "rationale": "NOAA shows 87% rain probability"
      }
    ],
    "rationale": "Weighted consensus score 0.21 below reject threshold 0.30"
  },
  "validator_names": ["source", "consistency", "reasoning"],
  "final_verdict": "rejected",
  "confidence_score": 0.21,
  "recorded_at": "2026-06-20T21:00:00Z"
}
```

---

### GET /workflows/{workflow_id}/state

Get the current canonical state of a workflow.

**Response** `200 OK`:
```json
{
  "workflow_id": "wf-demo-001",
  "accepted_claims": [ { "...": "Claim objects" } ],
  "pending_claims": [ { "...": "Claim objects" } ],
  "agent_trust_scores": [
    {
      "agent_id": "agent-weather-001",
      "score": 0.42,
      "total_claims": 5,
      "accepted_claims": 2,
      "rejected_claims": 3,
      "last_updated": "2026-06-20T21:00:00Z"
    }
  ]
}
```

---

### GET /agents/trust

Get trust scores for all known agents.

**Response** `200 OK`:
```json
[
  {
    "agent_id": "agent-weather-001",
    "score": 0.42,
    "total_claims": 5,
    "accepted_claims": 2,
    "rejected_claims": 3,
    "last_updated": "2026-06-20T21:00:00Z"
  }
]
```

---

### GET /validators/reliability

Get reliability scores for all validators.

**Response** `200 OK`:
```json
[
  {
    "validator_name": "source",
    "reliability": 0.88,
    "total_validations": 120,
    "correct_validations": 106,
    "last_updated": "2026-06-20T21:00:00Z"
  }
]
```

---

### GET /claims/quarantine

Get all quarantined (pending) claims.

**Response** `200 OK`:
```json
{
  "pending_claims": [ { "...": "Claim objects" } ],
  "count": 3
}
```

---

### GET /health

**Response** `200 OK`:
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## WebSocket

### WS /stream

Connect for real-time consensus events.

**Event types** (JSON):

```json
{
  "event_type": "claim_submitted",
  "claim_id": "uuid-v4",
  "workflow_id": "wf-demo-001",
  "data": { "agent_id": "agent-weather-001", "statement": "0% rain..." },
  "timestamp": "2026-06-20T21:00:00Z"
}
```

```json
{
  "event_type": "validator_result",
  "claim_id": "uuid-v4",
  "workflow_id": "wf-demo-001",
  "data": {
    "validator_name": "source",
    "verdict": "rejected",
    "confidence": 0.92
  },
  "timestamp": "2026-06-20T21:00:00Z"
}
```

```json
{
  "event_type": "consensus_reached",
  "claim_id": "uuid-v4",
  "workflow_id": "wf-demo-001",
  "data": {
    "verdict": "rejected",
    "score": 0.21,
    "rationale": "..."
  },
  "timestamp": "2026-06-20T21:00:00Z"
}
```

```json
{
  "event_type": "quarantined",
  "claim_id": "uuid-v4",
  "workflow_id": "wf-demo-001",
  "data": { "reason": "score below accept threshold, above reject threshold" },
  "timestamp": "2026-06-20T21:00:00Z"
}
```

---

## Error responses

All errors follow:
```json
{
  "error": "ValidationError",
  "message": "Source validator failed: ...",
  "claim_id": "uuid-v4"
}
```

HTTP status codes:
- `400` — bad request / invalid claim payload
- `404` — claim / workflow not found
- `422` — unprocessable entity (Pydantic validation error)
- `500` — internal pipeline error
