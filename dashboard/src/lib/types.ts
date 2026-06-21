export type Verdict = "accepted" | "rejected" | "needs_review";

export type FailureMode =
  | "no_evidence"
  | "contradicts_source"
  | "contradicts_workflow"
  | "missing_reasoning"
  | "unsupported_conclusion"
  | "invalid_assumption"
  | "contradictory_logic"
  | "low_confidence"
  | "none";

export interface Claim {
  id: string;
  agent_id: string;
  workflow_id: string;
  statement: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Evidence {
  source: string;
  url?: string;
  snippet: string;
  quality: number;
}

export interface ValidatorResult {
  validator_name: string;
  verdict: Verdict;
  confidence: number;
  evidence: Evidence[];
  failure_mode: FailureMode;
  reliability: number;
  rationale: string;
}

export interface ConsensusResult {
  claim_id: string;
  verdict: Verdict;
  score: number;
  validator_results: ValidatorResult[];
  rationale: string;
  created_at: string;
}

export interface ProvenanceRecord {
  claim_id: string;
  claim: Claim;
  consensus_result: ConsensusResult;
  validator_names: string[];
  final_verdict: Verdict;
  confidence_score: number;
  recorded_at: string;
}

export interface TrustScore {
  agent_id: string;
  score: number;
  total_claims: number;
  accepted_claims: number;
  rejected_claims: number;
  last_updated: string;
}

export interface ValidatorReliability {
  validator_name: string;
  reliability: number;
  total_validations: number;
  correct_validations: number;
  last_updated: string;
}

export interface ConsensusEvent {
  event_type:
    | "claim_submitted"
    | "validator_result"
    | "consensus_reached"
    | "quarantined";
  claim_id: string;
  workflow_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface QuarantineItem {
  claim: Claim;
  reason: string;
  quarantined_at: string;
}
