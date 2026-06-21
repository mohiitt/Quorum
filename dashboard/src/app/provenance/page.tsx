"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { VerdictBadge } from "@/components/consensus/verdict-badge";
import { MOCK_PROVENANCE } from "@/lib/mock";
import type { ProvenanceRecord } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Fragment } from "react";

function formatDate(iso: string) {
  return new Date(iso).toISOString().slice(11, 19) + " UTC";
}

function RecordDetail({ record }: { record: ProvenanceRecord }) {
  return (
    <div className="space-y-4 p-4 bg-zinc-800 rounded-md border border-zinc-700">
      <div>
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
          Claim Statement
        </p>
        <p className="text-sm text-zinc-100">{record.claim.statement}</p>
        <p className="font-mono text-xs text-zinc-500 mt-1">
          Claim ID: {record.claim_id}
        </p>
      </div>

      <div>
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          Validator Results
        </p>
        <div className="space-y-2">
          {record.consensus_result.validator_results.map((vr) => (
            <div
              key={vr.validator_name}
              className="flex items-start gap-3 rounded-md bg-zinc-900 p-3 border border-zinc-700"
            >
              <VerdictBadge verdict={vr.verdict} className="mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-zinc-200 capitalize">
                  {vr.validator_name}
                </p>
                <p className="text-xs text-zinc-400 mt-0.5">{vr.rationale}</p>
                {vr.evidence.length > 0 && (
                  <p className="font-mono text-xs text-zinc-500 mt-1">
                    Evidence: {vr.evidence[0].snippet.slice(0, 80)}…
                  </p>
                )}
              </div>
              <span className="font-mono text-xs text-zinc-500 shrink-0">
                {(vr.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
          Consensus Rationale
        </p>
        <p className="text-xs text-zinc-300">
          {record.consensus_result.rationale}
        </p>
      </div>
    </div>
  );
}

export default function ProvenancePage() {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="flex flex-col">
      <Header
        title="Provenance Audit"
        description="Full audit trail — who said what, who validated it, and why it was accepted or rejected."
      />
      <div className="p-8">
        <Card className="border-zinc-800 bg-zinc-900 shadow-none">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-zinc-200">
              {MOCK_PROVENANCE.length} records
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead className="w-8" />
                  <TableHead className="text-xs text-zinc-500">
                    Claim ID
                  </TableHead>
                  <TableHead className="text-xs text-zinc-500">Agent</TableHead>
                  <TableHead className="text-xs text-zinc-500 max-w-xs">
                    Statement
                  </TableHead>
                  <TableHead className="text-xs text-zinc-500">
                    Verdict
                  </TableHead>
                  <TableHead className="text-xs text-zinc-500">
                    Confidence
                  </TableHead>
                  <TableHead className="text-xs text-zinc-500">
                    Recorded
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MOCK_PROVENANCE.map((record) => (
                  <Fragment key={record.claim_id}>
                    <TableRow
                      className="cursor-pointer hover:bg-zinc-800 border-zinc-800"
                      onClick={() =>
                        setExpanded(
                          expanded === record.claim_id ? null : record.claim_id
                        )
                      }
                    >
                      <TableCell className="py-3">
                        {expanded === record.claim_id ? (
                          <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-zinc-500" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-zinc-500">
                        {record.claim_id.slice(0, 16)}…
                      </TableCell>
                      <TableCell className="font-mono text-xs text-zinc-400">
                        {record.claim.agent_id}
                      </TableCell>
                      <TableCell className="max-w-xs text-sm text-zinc-100 truncate">
                        {record.claim.statement}
                      </TableCell>
                      <TableCell>
                        <VerdictBadge verdict={record.final_verdict} />
                      </TableCell>
                      <TableCell className="font-mono text-xs text-zinc-400">
                        {(record.confidence_score * 100).toFixed(0)}%
                      </TableCell>
                      <TableCell className="text-xs text-zinc-500">
                        {formatDate(record.recorded_at)}
                      </TableCell>
                    </TableRow>
                    {expanded === record.claim_id && (
                      <TableRow className="border-zinc-800">
                        <TableCell colSpan={7} className="py-2 px-4">
                          <RecordDetail record={record} />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
