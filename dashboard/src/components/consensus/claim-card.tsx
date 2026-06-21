import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { VerdictBadge } from "./verdict-badge";
import type { ConsensusResult } from "@/lib/types";

interface ClaimCardProps {
  result: ConsensusResult;
  statement: string;
  agentId: string;
}

const VALIDATOR_COLORS: Record<string, string> = {
  accepted: "bg-emerald-400",
  rejected: "bg-red-400",
  needs_review: "bg-amber-400",
};

export function ClaimCard({ result, statement, agentId }: ClaimCardProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-900 shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-zinc-100">
              {statement}
            </p>
            <p className="mt-0.5 font-mono text-xs text-zinc-500">{agentId}</p>
          </div>
          <VerdictBadge verdict={result.verdict} />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Validator pipeline */}
        <div className="flex items-center gap-2">
          {result.validator_results.map((vr) => (
            <div key={vr.validator_name} className="flex items-center gap-1.5">
              <span
                className={`h-2.5 w-2.5 rounded-full ${VALIDATOR_COLORS[vr.verdict] ?? "bg-zinc-600"}`}
              />
              <span className="text-xs font-medium text-zinc-300 capitalize">
                {vr.validator_name}
              </span>
              <span className="text-xs text-zinc-500">
                {(vr.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>

        {/* Score bar */}
        <div className="mt-3 flex items-center gap-3">
          <div className="h-1.5 flex-1 rounded-full bg-zinc-800">
            <div
              className={`h-1.5 rounded-full transition-all ${
                result.score >= 0.7
                  ? "bg-emerald-400"
                  : result.score <= 0.3
                    ? "bg-red-400"
                    : "bg-amber-400"
              }`}
              style={{ width: `${result.score * 100}%` }}
            />
          </div>
          <span className="font-mono text-xs text-zinc-500">
            {(result.score * 100).toFixed(0)}%
          </span>
        </div>

        <p className="mt-2 line-clamp-2 text-xs text-zinc-400">
          {result.rationale}
        </p>
      </CardContent>
    </Card>
  );
}
