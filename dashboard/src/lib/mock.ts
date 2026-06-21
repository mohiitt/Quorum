import type {
  Claim,
  ConsensusEvent,
  ConsensusResult,
  ProvenanceRecord,
  QuarantineItem,
  TrustScore,
  ValidatorReliability,
} from "./types";

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

export const MOCK_CLAIMS: Claim[] = [
  {
    id: "claim-weather-001",
    agent_id: "agent-weather-001",
    workflow_id: "wf-demo-001",
    statement: "There is a 0% chance of rain tomorrow.",
    payload: { forecast: { rain_probability: 0.0, source: "hallucinated" } },
    created_at: "2026-06-20T20:00:00Z",
  },
  {
    id: "claim-weather-002",
    agent_id: "agent-weather-fallback",
    workflow_id: "wf-demo-001",
    statement: "There is a 75% chance of rain tomorrow based on NOAA data.",
    payload: { forecast: { rain_probability: 0.75, source: "NOAA" } },
    created_at: "2026-06-20T20:01:30Z",
  },
  {
    id: "claim-sec-001",
    agent_id: "agent-financial-001",
    workflow_id: "wf-finance-002",
    statement: "ACME Corp reported $2.4B revenue in Q1 2026.",
    payload: { source: "sec_edgar", confidence: 0.91 },
    created_at: "2026-06-20T19:30:00Z",
  },
  {
    id: "claim-medical-001",
    agent_id: "agent-research-001",
    workflow_id: "wf-research-003",
    statement: "Clinical trials show a 40% reduction in symptoms.",
    payload: { pubmed_ids: ["38291047", "38201839"], confidence: 0.78 },
    created_at: "2026-06-20T18:45:00Z",
  },
  {
    id: "claim-logic-001",
    agent_id: "agent-planner-001",
    workflow_id: "wf-demo-001",
    statement: "Since it will not rain, no rain contingency budget is needed.",
    payload: { depends_on: "claim-weather-001" },
    created_at: "2026-06-20T20:00:30Z",
  },
];

// ---------------------------------------------------------------------------
// Consensus results
// ---------------------------------------------------------------------------

export const MOCK_CONSENSUS: ConsensusResult[] = [
  {
    claim_id: "claim-weather-001",
    verdict: "rejected",
    score: 0.18,
    validator_results: [
      {
        validator_name: "source",
        verdict: "rejected",
        confidence: 0.92,
        failure_mode: "contradicts_source",
        reliability: 0.88,
        rationale: "NOAA data shows 87% precipitation probability for the area.",
        evidence: [
          {
            source: "openweathermap",
            url: "https://api.openweathermap.org",
            snippet: "OpenWeatherMap: Rain (heavy intensity rain) in London",
            quality: 0.95,
          },
        ],
      },
      {
        validator_name: "consistency",
        verdict: "accepted",
        confidence: 0.7,
        failure_mode: "none",
        reliability: 0.85,
        rationale: "No prior claims in workflow to contradict.",
        evidence: [],
      },
      {
        validator_name: "reasoning",
        verdict: "rejected",
        confidence: 0.88,
        failure_mode: "unsupported_conclusion",
        reliability: 0.82,
        rationale: "Claim asserts 0% rain probability without citing any source.",
        evidence: [
          {
            source: "llm_analysis",
            snippet: "Claim asserts 0% rain probability without citing any source.",
            quality: 0.88,
          },
        ],
      },
    ],
    rationale:
      "Weighted consensus score 0.18 below reject threshold 0.30. Source validator found contradicting NOAA data.",
    created_at: "2026-06-20T20:00:15Z",
  },
  {
    claim_id: "claim-weather-002",
    verdict: "accepted",
    score: 0.84,
    validator_results: [
      {
        validator_name: "source",
        verdict: "accepted",
        confidence: 0.93,
        failure_mode: "none",
        reliability: 0.88,
        rationale: "NOAA data confirms 75% precipitation probability.",
        evidence: [
          {
            source: "openweathermap",
            url: "https://api.openweathermap.org",
            snippet: "OpenWeatherMap: Rain (moderate rain) in London",
            quality: 0.95,
          },
        ],
      },
      {
        validator_name: "consistency",
        verdict: "accepted",
        confidence: 0.8,
        failure_mode: "none",
        reliability: 0.85,
        rationale: "No contradiction with workflow state.",
        evidence: [],
      },
      {
        validator_name: "reasoning",
        verdict: "accepted",
        confidence: 0.87,
        failure_mode: "none",
        reliability: 0.82,
        rationale: "Claim cites NOAA as source. Logical structure is sound.",
        evidence: [
          {
            source: "llm_analysis",
            snippet: "Claim cites NOAA as source. Logical structure is sound.",
            quality: 0.87,
          },
        ],
      },
    ],
    rationale: "Weighted consensus score 0.84 exceeds accept threshold 0.70.",
    created_at: "2026-06-20T20:01:45Z",
  },
  {
    claim_id: "claim-sec-001",
    verdict: "accepted",
    score: 0.81,
    validator_results: [
      {
        validator_name: "source",
        verdict: "accepted",
        confidence: 0.89,
        failure_mode: "none",
        reliability: 0.88,
        rationale: "SEC EDGAR filing corroborates Q1 2026 revenue figure.",
        evidence: [
          {
            source: "sec_edgar",
            url: "https://efts.sec.gov",
            snippet: "ACME Corp 10-Q: Total revenue $2,401,233,000 Q1 2026",
            quality: 0.92,
          },
        ],
      },
      {
        validator_name: "consistency",
        verdict: "accepted",
        confidence: 0.8,
        failure_mode: "none",
        reliability: 0.85,
        rationale: "No conflicting revenue claims in workflow.",
        evidence: [],
      },
      {
        validator_name: "reasoning",
        verdict: "accepted",
        confidence: 0.82,
        failure_mode: "none",
        reliability: 0.82,
        rationale: "Claim is specific and cites a verifiable filing.",
        evidence: [],
      },
    ],
    rationale: "Weighted consensus score 0.81 exceeds accept threshold 0.70.",
    created_at: "2026-06-20T19:30:20Z",
  },
  {
    claim_id: "claim-medical-001",
    verdict: "needs_review",
    score: 0.52,
    validator_results: [
      {
        validator_name: "source",
        verdict: "accepted",
        confidence: 0.71,
        failure_mode: "none",
        reliability: 0.88,
        rationale: "PubMed found 4 relevant articles supporting the claim.",
        evidence: [
          {
            source: "pubmed",
            url: "https://pubmed.ncbi.nlm.nih.gov",
            snippet: "PubMed: 4 article(s) found. Top IDs: ['38291047', '38201839']",
            quality: 0.7,
          },
        ],
      },
      {
        validator_name: "consistency",
        verdict: "needs_review",
        confidence: 0.5,
        failure_mode: "low_confidence",
        reliability: 0.85,
        rationale:
          "Prior claim in workflow stated 35% reduction — minor discrepancy.",
        evidence: [
          { source: "workflow_memory", snippet: "Prior claim: 35% reduction in symptoms.", quality: 0.7 },
        ],
      },
      {
        validator_name: "reasoning",
        verdict: "accepted",
        confidence: 0.75,
        failure_mode: "none",
        reliability: 0.82,
        rationale: "Percentage reduction is a verifiable statistical claim.",
        evidence: [],
      },
    ],
    rationale:
      "Weighted consensus score 0.52 between thresholds. Quarantined for review.",
    created_at: "2026-06-20T18:45:30Z",
  },
  {
    claim_id: "claim-logic-001",
    verdict: "rejected",
    score: 0.12,
    validator_results: [
      {
        validator_name: "source",
        verdict: "rejected",
        confidence: 0.85,
        failure_mode: "no_evidence",
        reliability: 0.88,
        rationale: "Claim depends on rejected weather claim.",
        evidence: [],
      },
      {
        validator_name: "consistency",
        verdict: "rejected",
        confidence: 0.92,
        failure_mode: "contradicts_workflow",
        reliability: 0.85,
        rationale: "Workflow state shows weather claim was rejected.",
        evidence: [
          {
            source: "workflow_memory",
            snippet: "claim-weather-001 was REJECTED: contradicts NOAA data.",
            quality: 0.95,
          },
        ],
      },
      {
        validator_name: "reasoning",
        verdict: "rejected",
        confidence: 0.9,
        failure_mode: "invalid_assumption",
        reliability: 0.82,
        rationale: "Assumes 0% rain which was disproven — invalid assumption.",
        evidence: [],
      },
    ],
    rationale: "Weighted consensus score 0.12 below reject threshold 0.30.",
    created_at: "2026-06-20T20:00:45Z",
  },
];

// ---------------------------------------------------------------------------
// Provenance records
// ---------------------------------------------------------------------------

export const MOCK_PROVENANCE: ProvenanceRecord[] = MOCK_CLAIMS.map(
  (claim, i) => ({
    claim_id: claim.id,
    claim,
    consensus_result: MOCK_CONSENSUS[i],
    validator_names: ["source", "consistency", "reasoning"],
    final_verdict: MOCK_CONSENSUS[i].verdict,
    confidence_score: MOCK_CONSENSUS[i].score,
    recorded_at: MOCK_CONSENSUS[i].created_at,
  })
);

// ---------------------------------------------------------------------------
// Trust scores
// ---------------------------------------------------------------------------

export const MOCK_TRUST: TrustScore[] = [
  {
    agent_id: "agent-weather-001",
    score: 0.2,
    total_claims: 5,
    accepted_claims: 1,
    rejected_claims: 4,
    last_updated: "2026-06-20T20:01:00Z",
  },
  {
    agent_id: "agent-weather-fallback",
    score: 0.92,
    total_claims: 12,
    accepted_claims: 11,
    rejected_claims: 1,
    last_updated: "2026-06-20T20:02:00Z",
  },
  {
    agent_id: "agent-financial-001",
    score: 0.87,
    total_claims: 23,
    accepted_claims: 20,
    rejected_claims: 3,
    last_updated: "2026-06-20T19:31:00Z",
  },
  {
    agent_id: "agent-research-001",
    score: 0.68,
    total_claims: 19,
    accepted_claims: 13,
    rejected_claims: 6,
    last_updated: "2026-06-20T18:46:00Z",
  },
];

// ---------------------------------------------------------------------------
// Validator reliability
// ---------------------------------------------------------------------------

export const MOCK_RELIABILITY: ValidatorReliability[] = [
  {
    validator_name: "source",
    reliability: 0.88,
    total_validations: 120,
    correct_validations: 106,
    last_updated: "2026-06-20T20:02:00Z",
  },
  {
    validator_name: "consistency",
    reliability: 0.85,
    total_validations: 120,
    correct_validations: 102,
    last_updated: "2026-06-20T20:02:00Z",
  },
  {
    validator_name: "reasoning",
    reliability: 0.82,
    total_validations: 120,
    correct_validations: 98,
    last_updated: "2026-06-20T20:02:00Z",
  },
];

// ---------------------------------------------------------------------------
// Quarantine items
// ---------------------------------------------------------------------------

export const MOCK_QUARANTINE: QuarantineItem[] = [
  {
    claim: MOCK_CLAIMS[3],
    reason: "Score 0.52 between accept (0.70) and reject (0.30) thresholds",
    quarantined_at: "2026-06-20T18:45:30Z",
  },
  {
    claim: {
      id: "claim-pending-001",
      agent_id: "agent-research-002",
      workflow_id: "wf-research-003",
      statement: "Mortality rates decreased by 12% following the intervention.",
      payload: { confidence: 0.55 },
      created_at: "2026-06-20T17:00:00Z",
    },
    reason: "Score 0.48 between accept (0.70) and reject (0.30) thresholds",
    quarantined_at: "2026-06-20T17:00:20Z",
  },
];

// ---------------------------------------------------------------------------
// Live event stream (simulated)
// ---------------------------------------------------------------------------

export const DEMO_EVENT_SEQUENCE: ConsensusEvent[] = [
  {
    event_type: "claim_submitted",
    claim_id: "claim-weather-001",
    workflow_id: "wf-demo-001",
    data: {
      agent_id: "agent-weather-001",
      statement: "There is a 0% chance of rain tomorrow.",
    },
    timestamp: "2026-06-20T20:00:00Z",
  },
  {
    event_type: "validator_result",
    claim_id: "claim-weather-001",
    workflow_id: "wf-demo-001",
    data: { validator_name: "source", verdict: "rejected", confidence: 0.92 },
    timestamp: "2026-06-20T20:00:05Z",
  },
  {
    event_type: "validator_result",
    claim_id: "claim-weather-001",
    workflow_id: "wf-demo-001",
    data: { validator_name: "consistency", verdict: "accepted", confidence: 0.7 },
    timestamp: "2026-06-20T20:00:08Z",
  },
  {
    event_type: "validator_result",
    claim_id: "claim-weather-001",
    workflow_id: "wf-demo-001",
    data: { validator_name: "reasoning", verdict: "rejected", confidence: 0.88 },
    timestamp: "2026-06-20T20:00:12Z",
  },
  {
    event_type: "consensus_reached",
    claim_id: "claim-weather-001",
    workflow_id: "wf-demo-001",
    data: { verdict: "rejected", score: 0.18, rationale: "Score below reject threshold" },
    timestamp: "2026-06-20T20:00:15Z",
  },
  {
    event_type: "claim_submitted",
    claim_id: "claim-weather-002",
    workflow_id: "wf-demo-001",
    data: {
      agent_id: "agent-weather-fallback",
      statement: "There is a 75% chance of rain tomorrow based on NOAA data.",
    },
    timestamp: "2026-06-20T20:01:30Z",
  },
  {
    event_type: "validator_result",
    claim_id: "claim-weather-002",
    workflow_id: "wf-demo-001",
    data: { validator_name: "source", verdict: "accepted", confidence: 0.93 },
    timestamp: "2026-06-20T20:01:35Z",
  },
  {
    event_type: "consensus_reached",
    claim_id: "claim-weather-002",
    workflow_id: "wf-demo-001",
    data: { verdict: "accepted", score: 0.84, rationale: "Score exceeds accept threshold" },
    timestamp: "2026-06-20T20:01:45Z",
  },
];
