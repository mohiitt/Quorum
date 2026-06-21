"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import type { QuarantineItem } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Lock, CheckCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchQuarantine(): Promise<QuarantineItem[]> {
  try {
    const res = await fetch(`${API}/claims/quarantine`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    const raw: QuarantineItem[] = (data.pending_claims ?? []).map(
      (item: Record<string, unknown>) => ({
        claim: item.claim as QuarantineItem["claim"],
        reason: (item.reason as string) ?? "Score between accept/reject thresholds",
        quarantined_at: (item.quarantined_at as string) ?? new Date().toISOString(),
      })
    );
    // Deduplicate by claim id
    const seen = new Set<string>();
    return raw.filter((q) => {
      const id = q.claim?.id;
      if (!id || seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  } catch {
    return [];
  }
}
function QuarantineCard({
  item,
  onRelease,
}: {
  item: QuarantineItem;
  onRelease: (id: string) => void;
}) {
  const [released, setReleased] = useState(false);

  const handleRelease = () => {
    setReleased(true);
    onRelease(item.claim.id);
  };

  return (
    <Card
      className={`border-zinc-800 bg-zinc-900 shadow-none transition-opacity ${released ? "opacity-40" : ""}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5 shrink-0 text-amber-400" />
            <Badge
              variant="outline"
              className="bg-amber-950/40 text-amber-300 border-amber-800 font-medium"
            >
              Quarantined
            </Badge>
          </div>
          {released ? (
            <div className="flex items-center gap-1 text-xs text-emerald-400">
              <CheckCircle className="h-3.5 w-3.5" />
              Released
            </div>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-50"
              onClick={handleRelease}
            >
              Release
            </Button>
          )}
        </div>
        <CardTitle className="mt-2 text-sm font-medium text-zinc-100 leading-snug">
          {item.claim.statement}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs">
          <div className="text-zinc-500">Agent</div>
          <div className="font-mono text-zinc-300">{item.claim.agent_id}</div>
          <div className="text-zinc-500">Workflow</div>
          <div className="font-mono text-zinc-300">{item.claim.workflow_id}</div>
          <div className="text-zinc-500">Quarantined at</div>
          <div className="text-zinc-300" suppressHydrationWarning>
            {new Date(item.quarantined_at).toISOString().slice(11, 19)} UTC
          </div>
        </div>
        <div className="rounded-md bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
          <span className="font-semibold">Reason: </span>
          {item.reason}
        </div>
      </CardContent>
    </Card>
  );
}

export default function QuarantinePage() {
  const [items, setItems] = useState<QuarantineItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuarantine()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  const handleRelease = (id: string) => {
    setTimeout(() => setItems((prev) => prev.filter((i) => i.claim.id !== id)), 1500);
  };

  return (
    <div className="flex flex-col">
      <Header
        title="Quarantine"
        description="Claims with inconclusive consensus scores held pending further validation."
      />
      <div className="p-8">
        {loading ? (
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
            Loading…
          </div>
        ) : items.length === 0 ? (
          <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-zinc-700 text-sm text-zinc-500">
            No quarantined claims — run the demo first.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {items.map((item) => (
              <QuarantineCard
                key={item.claim.id}
                item={item}
                onRelease={handleRelease}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
