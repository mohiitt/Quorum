"use client";

import { useEffect, useRef, useState } from "react";
import { Header } from "@/components/layout/header";
import { ClaimCard } from "@/components/consensus/claim-card";
import { MOCK_CONSENSUS, MOCK_CLAIMS } from "@/lib/mock";
import type { ConsensusResult } from "@/lib/types";
import { Button } from "@/components/ui/button";

const USE_MOCK = false;

const DEMO_CLAIMS = [
  { statement: "Renewable energy ETFs have outperformed the S&P 500 by 4.2% YTD, driven by IRA subsidy tailwinds and falling solar module costs.", agent_id: "market-data-agent", workflow_id: "wf-demo-001", domain: "finance", confidence: 0.85 },
  { statement: "A fabricated Goldman Sachs report guarantees 40% risk-free returns on fossil fuel investments in 2025.", agent_id: "bad-finance-agent", workflow_id: "wf-demo-001", domain: "finance", confidence: 0.95 },
  { statement: "Crude oil futures are pricing in a $15/barrel risk premium due to Middle East supply uncertainty, per CME open interest data.", agent_id: "risk-assessor", workflow_id: "wf-demo-001", domain: "finance", confidence: 0.82 },
  { statement: "The Federal Reserve has committed to cutting rates by 200 basis points before end of 2025 to support clean energy infrastructure bonds.", agent_id: "news-analysis-agent", workflow_id: "wf-demo-001", domain: "finance", confidence: 0.9 },
];

let demoIndex = 0;

async function postDemoClaim() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const claim = DEMO_CLAIMS[demoIndex % DEMO_CLAIMS.length];
  demoIndex++;
  await fetch(`${apiUrl}/claims/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(claim),
  }).catch(() => {});
}

export default function ConsensuPage() {
  const [visible, setVisible] = useState<ConsensusResult[]>([]);
  const [index, setIndex] = useState(0);
  const [posting, setPosting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const closedIntentionally = useRef(false);

  useEffect(() => {
    if (!USE_MOCK) {
      closedIntentionally.current = false;
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/stream";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          const event = JSON.parse(evt.data);
          if (event.event_type === "consensus_reached" && event.data?.consensus_result) {
            const result: ConsensusResult = event.data.consensus_result;
            setVisible((prev) => {
              if (prev.some((r) => r.claim_id === result.claim_id)) return prev;
              return [result, ...prev].slice(0, 20);
            });
          }
        } catch {}
      };

      return () => {
        closedIntentionally.current = true;
        ws.close();
      };
    }

    // Mock: reveal results one at a time every 1.8 s
    if (index >= MOCK_CONSENSUS.length) return;
    const timer = setTimeout(() => {
      setVisible((prev) => [MOCK_CONSENSUS[index], ...prev]);
      setIndex((i) => i + 1);
    }, 1800);
    return () => clearTimeout(timer);
  }, [USE_MOCK ? index : null]);

  const handleDemo = async () => {
    setPosting(true);
    await postDemoClaim();
    setTimeout(() => setPosting(false), 1500);
  };

  return (
    <div className="flex flex-col">
      <Header
        title="Live Consensus"
        description="Claims flowing through the validation pipeline in real time."
      />
      <div className="flex-1 space-y-4 p-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Streaming — workflow <span className="font-mono ml-1">wf-demo-001</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-50"
            onClick={handleDemo}
            disabled={posting}
          >
            {posting ? "Submitting…" : "⚡ Submit Demo Claim"}
          </Button>
        </div>

        {visible.length === 0 && (
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
            Waiting for claims…
          </div>
        )}

        <div className="space-y-3">
          {visible.map((result) => (
            <ClaimCard
              key={result.claim_id}
              result={result}
              statement={(result as ConsensusResult & { statement?: string }).statement ?? result.claim_id}
              agentId={(result as ConsensusResult & { agent_id?: string }).agent_id ?? "unknown"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
