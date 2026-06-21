"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { TrustScore, ValidatorReliability } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchTrust(): Promise<TrustScore[]> {
  try {
    const res = await fetch(`${API}/agents/trust`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

async function fetchReliability(): Promise<ValidatorReliability[]> {
  try {
    const res = await fetch(`${API}/validators/reliability`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function scoreColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

function progressColor(score: number): string {
  if (score >= 0.7) return "[&>div]:bg-emerald-400";
  if (score >= 0.4) return "[&>div]:bg-amber-400";
  return "[&>div]:bg-red-400";
}

export default function TrustPage() {
  const [trust, setTrust] = useState<TrustScore[]>([]);
  const [reliability, setReliability] = useState<ValidatorReliability[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchTrust(), fetchReliability()])
      .then(([t, r]) => { setTrust(t); setReliability(r); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col">
      <Header
        title="Trust Scores"
        description="Per-agent trust and validator reliability, updated after each consensus round."
      />
      <div className="space-y-8 p-8">
        {/* Agent trust */}
        <section>
          <h2 className="mb-4 text-sm font-semibold text-zinc-300">
            Agent Trust Scores
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {loading ? (
              <div className="col-span-2 text-center text-sm text-zinc-500 py-8">Loading…</div>
            ) : trust.length === 0 ? (
              <div className="col-span-2 text-center text-sm text-zinc-500 py-8">No trust data yet — run the demo first.</div>
            ) : null}
            {trust.map((ts) => (
              <Card key={ts.agent_id} className="border-zinc-800 bg-zinc-900 shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="font-mono text-sm text-zinc-100">
                    {ts.agent_id}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-end justify-between">
                    <span
                      className={`text-3xl font-bold tabular-nums ${scoreColor(ts.score)}`}
                    >
                      {(ts.score * 100).toFixed(0)}
                      <span className="ml-0.5 text-lg text-zinc-500">%</span>
                    </span>
                    <span className="text-xs text-zinc-500">
                      trust score
                    </span>
                  </div>
                  <Progress
                    value={ts.score * 100}
                    className={`h-2 bg-zinc-800 ${progressColor(ts.score)}`}
                  />
                  <div className="flex justify-between text-xs text-zinc-400">
                    <span>
                      <span className="font-medium text-emerald-400">
                        {ts.accepted_claims}
                      </span>{" "}
                      accepted
                    </span>
                    <span>
                      <span className="font-medium text-red-400">
                        {ts.rejected_claims}
                      </span>{" "}
                      rejected
                    </span>
                    <span>{ts.total_claims} total</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Validator reliability */}
        <section>
          <h2 className="mb-4 text-sm font-semibold text-zinc-300">
            Validator Reliability
          </h2>
          <Card className="border-zinc-800 bg-zinc-900 shadow-none">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800">
                    <TableHead className="text-xs text-zinc-500">
                      Validator
                    </TableHead>
                    <TableHead className="text-xs text-zinc-500">
                      Reliability
                    </TableHead>
                    <TableHead className="text-xs text-zinc-500">
                      Correct / Total
                    </TableHead>
                    <TableHead className="text-xs text-zinc-500">
                      Last Updated
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reliability.map((r) => (
                    <TableRow key={r.validator_name} className="border-zinc-800">
                      <TableCell className="font-medium capitalize text-sm text-zinc-100">
                        {r.validator_name}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Progress
                            value={r.reliability * 100}
                            className="h-1.5 w-24 bg-zinc-800 [&>div]:bg-zinc-400"
                          />
                          <span className="font-mono text-xs text-zinc-300">
                            {(r.reliability * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-zinc-400">
                        {r.correct_validations} / {r.total_validations}
                      </TableCell>
                      <TableCell className="text-xs text-zinc-500" suppressHydrationWarning>
                        {new Date(r.last_updated).toISOString().slice(11, 19)} UTC
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
