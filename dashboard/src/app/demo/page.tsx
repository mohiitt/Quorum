"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Shield,
  ShieldOff,
  Loader2,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type AgentStatus = "pending" | "running" | "accepted" | "rejected" | "quarantined";

interface EvidenceItem {
  source: string;
  snippet: string;
  url?: string;
}

interface ValidatorBreakdown {
  name: string;
  verdict: string;
  confidence: number;
  rationale: string;
  evidence?: EvidenceItem[];
  score_source?: string;
}

interface AgentStep {
  agent_index: number;
  agent_id: string;
  agent_role: string;
  agent_icon: string;
  adversarial: boolean;
  claim: string;
  status: AgentStatus;
  verdict?: string;
  score?: number;
  rationale?: string;
  validator_breakdown?: ValidatorBreakdown[];
  blocked?: boolean;
}

interface DemoSummary {
  accepted: number;
  rejected: number;
  quarantined: number;
  protected_response: string;
  poisoned_response: string;
}

// ---------------------------------------------------------------------------
// Preset queries
// ---------------------------------------------------------------------------

const PRESET_QUERIES = [
  "What is the best investment strategy for renewable energy stocks given current market conditions?",
  "Should I take out a loan to invest in cryptocurrency based on recent market signals?",
  "What pharmaceutical stocks are safe to buy following the latest FDA announcements?",
  "Is now a good time to invest in AI infrastructure companies based on current trends?",
];

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === "pending") return <Clock className="h-4 w-4 text-zinc-500" />;
  if (status === "running") return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
  if (status === "accepted") return <CheckCircle className="h-4 w-4 text-emerald-400" />;
  if (status === "rejected") return <XCircle className="h-4 w-4 text-red-400" />;
  return <AlertTriangle className="h-4 w-4 text-amber-400" />;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === "accepted")
    return <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-700 text-xs">Accepted</Badge>;
  if (verdict === "rejected")
    return <Badge className="bg-red-500/20 text-red-300 border-red-700 text-xs">Blocked</Badge>;
  return <Badge className="bg-amber-500/20 text-amber-300 border-amber-700 text-xs">Quarantined</Badge>;
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 0.55 ? "bg-emerald-400" : score <= 0.42 ? "bg-red-400" : "bg-amber-400";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="h-1 flex-1 rounded-full bg-zinc-700">
        <div className={`h-1 rounded-full transition-all duration-700 ${color}`} style={{ width: `${score * 100}%` }} />
      </div>
      <span className="font-mono text-xs text-zinc-400">{(score * 100).toFixed(0)}%</span>
    </div>
  );
}

function AgentCard({ step, expanded, onToggle }: {
  step: AgentStep;
  expanded: boolean;
  onToggle: () => void;
}) {
  const borderColor =
    step.status === "accepted" ? "border-emerald-800/60" :
    step.status === "rejected" ? "border-red-800/60" :
    step.status === "quarantined" ? "border-amber-800/60" :
    step.status === "running" ? "border-blue-800/60" :
    "border-zinc-800";

  const bgGlow =
    step.status === "accepted" ? "bg-emerald-950/30" :
    step.status === "rejected" ? "bg-red-950/30" :
    step.status === "quarantined" ? "bg-amber-950/20" :
    step.status === "running" ? "bg-blue-950/20" :
    "bg-zinc-900/50";

  return (
    <div className={`rounded-lg border ${borderColor} ${bgGlow} transition-all duration-500`}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={onToggle}
        disabled={step.status === "pending"}
      >
        {/* Step number + icon */}
        <div className="flex items-center gap-2 shrink-0 mt-0.5">
          <span className="text-lg">{step.agent_icon}</span>
          <StatusIcon status={step.status} />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-zinc-100">{step.agent_role}</span>
            {step.adversarial && step.status !== "pending" && (
              <Badge className="bg-red-950/50 text-red-400 border-red-800 text-[10px] px-1.5">
                ⚠ Compromised
              </Badge>
            )}
            {step.verdict && <VerdictBadge verdict={step.verdict} />}
          </div>
          {step.status !== "pending" && (
            <p className="text-xs text-zinc-400 mt-0.5 line-clamp-1">
              &ldquo;{step.claim}&rdquo;
            </p>
          )}
          {step.status === "running" && (
            <p className="text-xs text-blue-400 mt-0.5 animate-pulse">Validating with Quorum…</p>
          )}
          {step.verdict && step.score !== undefined && <ScoreBar score={step.score} />}
        </div>

        {/* Expand chevron */}
        {step.status !== "pending" && step.status !== "running" && (
          <div className="shrink-0 mt-1 text-zinc-500">
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </div>
        )}
      </button>

      {/* Expanded detail */}
      {expanded && step.verdict && (
        <div className="px-4 pb-4 space-y-3 border-t border-zinc-800/60 pt-3">
          {/* Full claim */}
          <div>
            <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1">Agent Claim</p>
            <p className="text-xs text-zinc-200 bg-zinc-800/50 rounded px-2 py-1.5">&ldquo;{step.claim}&rdquo;</p>
          </div>

          {/* Quorum rationale */}
          <div>
            <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1">Quorum Rationale</p>
            <p className="text-xs text-zinc-300">{step.rationale}</p>
          </div>

          {/* Validator breakdown */}
          {step.validator_breakdown && step.validator_breakdown.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">Validator Breakdown</p>
              <div className="space-y-1.5">
                {step.validator_breakdown.map((vb) => (
                  <div key={vb.name} className="text-xs bg-zinc-800/40 rounded px-2 py-2 space-y-1">
                    {/* Header row: icon + name + score */}
                    <div className="flex items-center gap-1.5">
                      <span className={`font-mono shrink-0 ${
                        vb.verdict === "accepted" ? "text-emerald-400" :
                        vb.verdict === "rejected" ? "text-red-400" : "text-amber-400"
                      }`}>
                        {vb.verdict === "accepted" ? "✓" : vb.verdict === "rejected" ? "✗" : "~"}
                      </span>
                      <span className="text-zinc-300 font-medium capitalize">{vb.name.replace("ValidatorName.", "")}</span>
                      <span className="text-zinc-500">({(vb.confidence * 100).toFixed(0)}%)</span>
                    </div>

                    {/* Rationale */}
                    {vb.rationale && (
                      <p className="text-zinc-400 ml-4 line-clamp-3">{vb.rationale}</p>
                    )}

                    {/* Score derivation (source validator only) */}
                    {vb.score_source && (
                      <p className="text-zinc-600 ml-4 text-[10px] italic">{vb.score_source}</p>
                    )}

                    {/* Evidence citations (source validator only) */}
                    {vb.name === "source" && vb.evidence && vb.evidence.length > 0 && (
                      <div className="ml-4 mt-1 space-y-0.5">
                        <p className="text-[10px] text-zinc-600 font-semibold uppercase tracking-wider">Sources consulted</p>
                        {vb.evidence.map((ev, i) => (
                          <div key={i} className="text-[10px] text-zinc-500 border-l-2 border-zinc-700/70 pl-1.5 py-0.5">
                            <span className="font-mono text-zinc-600 uppercase text-[9px]">{ev.source}</span>
                            <span className="text-zinc-600"> — </span>
                            <span className="text-zinc-400">{ev.snippet}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Explicit no-source message */}
                    {vb.name === "source" && (!vb.evidence || vb.evidence.length === 0) && (
                      <p className="text-[10px] text-zinc-600 ml-4 italic">No external sources retrieved.</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DemoPage() {
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [agents, setAgents] = useState<AgentStep[]>([]);
  const [summary, setSummary] = useState<DemoSummary | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const abortRef = useRef(false);
  const closedIntentionally = useRef(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/stream";

  // ---------------------------------------------------------------------------
  // WebSocket — always connected
  // ---------------------------------------------------------------------------

  useEffect(() => {
    closedIntentionally.current = false;

    const connect = () => {
      if (closedIntentionally.current) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);

      ws.onclose = () => {
        setWsConnected(false);
        if (!closedIntentionally.current) {
          // Back-off reconnect — only while component is mounted
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };

      ws.onmessage = (evt) => {
        try {
          const event = JSON.parse(evt.data);
          handleWsEvent(event);
        } catch {}
      };
    };

    connect();

    return () => {
      // Mark as intentional so onclose doesn't schedule a reconnect
      closedIntentionally.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  function handleWsEvent(event: Record<string, unknown>) {
    const type = event.event_type as string;

    if (type === "demo_start") {
      // Already handled in runDemo()
    } else if (type === "demo_agent_start") {
      const idx = event.agent_index as number;
      setAgents((prev) =>
        prev.map((a, i) =>
          i === idx ? { ...a, status: "running" as AgentStatus } : a
        )
      );
    } else if (type === "demo_agent_complete") {
      const idx = event.agent_index as number;
      const verdict = event.verdict as string;
      const status: AgentStatus =
        verdict === "accepted" ? "accepted" :
        verdict === "rejected" ? "rejected" : "quarantined";

      setAgents((prev) =>
        prev.map((a, i) =>
          i === idx
            ? {
                ...a,
                status,
                verdict,
                claim: (event.claim as string) || a.claim,
                score: event.score as number,
                rationale: event.rationale as string,
                validator_breakdown: event.validator_breakdown as ValidatorBreakdown[],
                blocked: event.blocked as boolean,
              }
            : a
        )
      );
      // Auto-expand rejected/quarantined agents
      if (verdict !== "accepted") {
        setExpanded(event.agent_id as string);
      }
    } else if (type === "demo_complete") {
      setSummary({
        accepted: (event.stats as Record<string, number>).accepted,
        rejected: (event.stats as Record<string, number>).rejected,
        quarantined: (event.stats as Record<string, number>).quarantined,
        protected_response: event.protected_response as string,
        poisoned_response: event.poisoned_response as string,
      });
      setRunning(false);
      setDone(true);
    }
  }

  // ---------------------------------------------------------------------------
  // Run demo
  // ---------------------------------------------------------------------------

  async function runDemo() {
    if (!query.trim() || running) return;
    abortRef.current = false;
    setDone(false);
    setSummary(null);
    setExpanded(null);

    // Initialise 5 pending agent slots
    const PERSONAS = [
      { id: "market-data-agent", role: "Market Data Agent", icon: "📊", adversarial: false },
      { id: "news-analysis-agent", role: "News Analysis Agent", icon: "📰", adversarial: true },
      { id: "trend-forecaster", role: "Trend Forecaster", icon: "📈", adversarial: false },
      { id: "risk-assessor", role: "Risk Assessment Agent", icon: "⚠️", adversarial: true },
      { id: "synthesis-agent", role: "Synthesis Agent", icon: "🧠", adversarial: false },
    ];

    setAgents(
      PERSONAS.map((p, i) => ({
        agent_index: i,
        agent_id: p.id,
        agent_role: p.role,
        agent_icon: p.icon,
        adversarial: p.adversarial,
        claim: "",
        status: "pending" as AgentStatus,
      }))
    );

    setRunning(true);

    try {
      const res = await fetch(`${API_URL}/demo/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      // Derive final output directly from the HTTP response — WS demo_complete
      // is a best-effort stream event that can be missed on slow connections.
      if (res.ok) {
        const data = await res.json();
        setSummary({
          accepted: data.accepted ?? 0,
          rejected: data.rejected ?? 0,
          quarantined: data.quarantined ?? 0,
          protected_response: data.protected_response ?? "",
          poisoned_response: data.poisoned_response ?? "",
        });
        setDone(true);
      }
    } catch (err) {
      // network error — nothing to show
    } finally {
      setRunning(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------

  const accepted = agents.filter((a) => a.status === "accepted").length;
  const rejected = agents.filter((a) => a.status === "rejected").length;
  const quarantined = agents.filter((a) => a.status === "quarantined").length;
  const blocked = rejected + quarantined;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col min-h-full bg-zinc-950">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900 px-8 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-50 flex items-center gap-2">
              <Shield className="h-5 w-5 text-emerald-400" />
              Live Demo — Multi-Agent Trust Pipeline
            </h1>
            <p className="mt-0.5 text-sm text-zinc-400">
              Enter a query as if using the ASI platform. Quorum intercepts each upstream agent's output in real-time.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className={`h-2 w-2 rounded-full ${wsConnected ? "bg-emerald-400" : "bg-red-500"}`} />
            {wsConnected ? "Live" : "Reconnecting…"}
          </div>
        </div>
      </div>

      <div className="flex-1 p-8 space-y-6 max-w-4xl w-full mx-auto">

        {/* Query input */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            User Query
          </label>
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-colors"
              placeholder="e.g. What investment strategy should I use for renewable energy stocks?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runDemo()}
              disabled={running}
            />
            <Button
              onClick={runDemo}
              disabled={!query.trim() || running || !wsConnected}
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 shrink-0"
            >
              {running ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Running…</>
              ) : (
                <><Zap className="h-4 w-4 mr-2" /> Run Query</>
              )}
            </Button>
          </div>

          {/* Preset queries */}
          {!running && !done && (
            <div className="flex flex-wrap gap-2">
              {PRESET_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => setQuery(q)}
                  className="text-xs text-zinc-400 hover:text-zinc-200 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded px-2 py-1 transition-colors text-left"
                >
                  {q.slice(0, 55)}…
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline visualization */}
        {agents.length > 0 && (
          <div className="space-y-3">
            {/* Stats bar */}
            {(accepted + rejected + quarantined) > 0 && (
              <div className="flex items-center gap-4 text-xs text-zinc-400 py-2 border-b border-zinc-800">
                <span className="text-zinc-300 font-medium">Quorum Pipeline</span>
                <span className="text-emerald-400">✓ {accepted} accepted</span>
                <span className="text-red-400">✗ {rejected} blocked</span>
                {quarantined > 0 && <span className="text-amber-400">⚠ {quarantined} quarantined</span>}
                {running && <span className="text-blue-400 animate-pulse ml-auto">Validating in real-time…</span>}
              </div>
            )}

            {/* Agent pipeline — vertical connected cards */}
            <div className="relative space-y-2">
              {agents.map((step, idx) => (
                <div key={step.agent_id} className="relative">
                  {/* Connector line */}
                  {idx < agents.length - 1 && (
                    <div className="absolute left-[22px] top-full w-px h-2 bg-zinc-700 z-10" />
                  )}
                  <AgentCard
                    step={step}
                    expanded={expanded === step.agent_id}
                    onToggle={() =>
                      setExpanded(expanded === step.agent_id ? null : step.agent_id)
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Final summary */}
        {done && summary && (
          <div className="space-y-4 pt-2">
            <div className="border-t border-zinc-800 pt-4">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                <Shield className="h-4 w-4 text-emerald-400" />
                Quorum Result
                <Badge className="ml-2 bg-emerald-500/20 text-emerald-300 border-emerald-700">
                  {blocked} threat{blocked !== 1 ? "s" : ""} intercepted
                </Badge>
              </h2>

              <div className="grid grid-cols-2 gap-4">
                {/* Protected response */}
                <div className="rounded-lg border border-emerald-800/50 bg-emerald-950/30 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-emerald-400" />
                    <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                      Protected Response
                    </p>
                  </div>
                  <p className="text-sm text-zinc-200 leading-relaxed">{summary.protected_response}</p>
                  <p className="text-xs text-emerald-600 mt-2">← What the user receives with Quorum</p>
                </div>

                {/* Poisoned response */}
                <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <ShieldOff className="h-4 w-4 text-red-400" />
                    <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">
                      Without Quorum
                    </p>
                  </div>
                  <p className="text-sm text-zinc-400 leading-relaxed line-through decoration-red-600/50">
                    {summary.poisoned_response}
                  </p>
                  <p className="text-xs text-red-700 mt-2">← Poisoned by {blocked} compromised agent{blocked !== 1 ? "s" : ""}</p>
                </div>
              </div>

              {/* Summary stats */}
              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 p-3">
                  <p className="text-2xl font-bold text-emerald-400">{summary.accepted}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">Claims Passed</p>
                </div>
                <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 p-3">
                  <p className="text-2xl font-bold text-red-400">{summary.rejected}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">Threats Blocked</p>
                </div>
                <div className="rounded-lg bg-zinc-800/50 border border-zinc-700 p-3">
                  <p className="text-2xl font-bold text-amber-400">{summary.quarantined}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">Quarantined</p>
                </div>
              </div>

              <Button
                variant="outline"
                className="mt-4 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                onClick={() => {
                  setDone(false);
                  setAgents([]);
                  setSummary(null);
                  setQuery("");
                }}
              >
                Run Another Query
              </Button>
            </div>
          </div>
        )}

        {/* Empty state — how it works */}
        {!running && !done && agents.length === 0 && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 text-center space-y-4">
            <div className="flex justify-center">
              <div className="h-12 w-12 rounded-full bg-emerald-950/50 border border-emerald-800 flex items-center justify-center">
                <Shield className="h-6 w-6 text-emerald-400" />
              </div>
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-200">How This Works</h3>
              <p className="text-sm text-zinc-400 mt-1 max-w-lg mx-auto">
                Enter any complex query. Quorum spawns 5 specialised agents — 2 are
                secretly compromised. Each agent's output is intercepted by the Quorum
                validation pipeline <strong className="text-zinc-200">before</strong> it
                reaches the next agent, preventing upstream poisoning.
              </p>
            </div>
            <div className="flex items-center justify-center gap-8 text-xs text-zinc-500">
              <span className="flex items-center gap-1.5"><span className="text-base">📊</span> Market Data Agent</span>
              <span className="text-zinc-700">→</span>
              <span className="flex items-center gap-1.5"><span className="text-base">📰</span> News Agent <span className="text-red-500">⚠</span></span>
              <span className="text-zinc-700">→</span>
              <span className="flex items-center gap-1.5"><Shield className="h-3 w-3 text-emerald-400" /> Quorum</span>
              <span className="text-zinc-700">→</span>
              <span className="flex items-center gap-1.5"><span className="text-base">🧠</span> Synthesis Agent</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
