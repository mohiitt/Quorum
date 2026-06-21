/**
 * API client — returns mock data during development (Phase 8).
 * Swap NEXT_PUBLIC_API_URL env var and remove mock imports in Phase 9.
 */

import {
  MOCK_PROVENANCE,
  MOCK_QUARANTINE,
  MOCK_RELIABILITY,
  MOCK_TRUST,
  MOCK_CONSENSUS,
} from "./mock";
import type {
  ProvenanceRecord,
  QuarantineItem,
  TrustScore,
  ValidatorReliability,
  ConsensusResult,
} from "./types";

const USE_MOCK = false;

export async function getProvenance(): Promise<ProvenanceRecord[]> {
  if (USE_MOCK) return MOCK_PROVENANCE;
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/claims/provenance`
  );
  if (!res.ok) return [];
  return res.json();
}

export async function getTrustScores(): Promise<TrustScore[]> {
  if (USE_MOCK) return MOCK_TRUST;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/agents/trust`);
  return res.json();
}

export async function getValidatorReliability(): Promise<ValidatorReliability[]> {
  if (USE_MOCK) return MOCK_RELIABILITY;
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/validators/reliability`
  );
  return res.json();
}

export async function getQuarantine(): Promise<QuarantineItem[]> {
  if (USE_MOCK) return MOCK_QUARANTINE;
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/claims/quarantine`
  );
  const data = await res.json();
  return data.pending_claims ?? [];
}

export async function getRecentConsensus(): Promise<ConsensusResult[]> {
  if (USE_MOCK) return MOCK_CONSENSUS;
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/consensus/recent`
  );
  if (!res.ok) return [];
  return res.json();
}
