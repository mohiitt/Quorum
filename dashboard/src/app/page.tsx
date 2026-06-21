import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { CheckCircle, XCircle, AlertTriangle, Globe, GitBranch, Brain, ArrowRight, Zap, Shield, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

const VALIDATORS = [
  {
    icon: Globe,
    name: "Source",
    color: "emerald",
    description: "Live web evidence via DuckDuckGo, Wikipedia, and Browserbase. Scores real-world support for every claim.",
    badge: "Web Search",
  },
  {
    icon: GitBranch,
    name: "Consistency",
    color: "blue",
    description: "Cross-checks the claim against everything already accepted in the session. Catches contradictions before they propagate.",
    badge: "Memory",
  },
  {
    icon: Brain,
    name: "Reasoning",
    color: "violet",
    description: "Claude evaluates internal coherence. Flags unsupported conclusions, circular logic, and category errors.",
    badge: "LLM",
  },
];

const VERDICTS = [
  { icon: CheckCircle, label: "Accepted", color: "text-emerald-400", bg: "bg-emerald-950/40 border-emerald-800/60" },
  { icon: XCircle,    label: "Rejected",  color: "text-red-400",     bg: "bg-red-950/40 border-red-800/60" },
  { icon: AlertTriangle, label: "Needs Review", color: "text-amber-400", bg: "bg-amber-950/40 border-amber-800/60" },
];

const colorMap: Record<string, { icon: string; card: string; badge: string; border: string }> = {
  emerald: {
    icon: "text-emerald-400",
    card: "bg-emerald-950/20 border-emerald-800/40 hover:border-emerald-700/60",
    badge: "bg-emerald-950/50 text-emerald-300 border-emerald-800",
    border: "border-l-emerald-500",
  },
  blue: {
    icon: "text-blue-400",
    card: "bg-blue-950/20 border-blue-800/40 hover:border-blue-700/60",
    badge: "bg-blue-950/50 text-blue-300 border-blue-800",
    border: "border-l-blue-500",
  },
  violet: {
    icon: "text-violet-400",
    card: "bg-violet-950/20 border-violet-800/40 hover:border-violet-700/60",
    badge: "bg-violet-950/50 text-violet-300 border-violet-800",
    border: "border-l-violet-500",
  },
};

export default function LandingPage() {
  return (
    <div className="min-h-full bg-zinc-950 text-zinc-100">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b border-zinc-800/60 px-8 py-16">
        {/* subtle grid background */}
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div className="relative max-w-3xl">
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-xs font-mono">v1.0</Badge>
            <Badge className="bg-violet-950/50 text-violet-300 border-violet-800 text-xs">Agentverse Ready</Badge>
          </div>
          <h1 className="text-5xl font-bold tracking-tight mb-3">
            <span className="bg-gradient-to-r from-zinc-100 via-zinc-300 to-zinc-500 bg-clip-text text-transparent">
              Quorum
            </span>
          </h1>
          <p className="text-xl text-zinc-400 mb-2 font-light">
            Multi-agent trust &amp; consensus for AI pipelines.
          </p>
          <p className="text-sm text-zinc-500 mb-8 max-w-xl">
            Every agent claim runs through three independent validators — Source, Consistency, and Reasoning —
            before reaching consensus. Built on Fetch.ai uAgents, queryable from ASI:One.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/demo"
              className={cn(buttonVariants({ size: "lg" }), "bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-semibold")}
            >
              Try the Demo <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <a
              href="https://agentverse.ai"
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ size: "lg", variant: "outline" }), "border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100")}
            >
              <Bot className="mr-2 h-4 w-4" /> Find on Agentverse
            </a>
          </div>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="border-b border-zinc-800/60 px-8 py-5">
        <div className="flex flex-wrap gap-8">
          {[
            { label: "Validators", value: "3" },
            { label: "Consensus score", value: "0 – 1" },
            { label: "Verdicts", value: "3" },
            { label: "Agentverse protocol", value: "Chat + Custom" },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-zinc-100 tabular-nums">{value}</span>
              <span className="text-xs text-zinc-500 uppercase tracking-wide">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Validators ── */}
      <section className="px-8 py-10 border-b border-zinc-800/60">
        <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest mb-5 flex items-center gap-2">
          <Zap className="h-3 w-3" /> Three-Layer Pipeline
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {VALIDATORS.map(({ icon: Icon, name, color, description, badge }) => {
            const c = colorMap[color];
            return (
              <div
                key={name}
                className={`rounded-lg border ${c.card} border-l-4 ${c.border} px-5 py-4 space-y-3 transition-colors`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${c.icon}`} />
                    <span className="font-semibold text-zinc-100">{name}</span>
                  </div>
                  <Badge variant="outline" className={`text-[10px] ${c.badge}`}>{badge}</Badge>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">{description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Verdicts ── */}
      <section className="px-8 py-10 border-b border-zinc-800/60">
        <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest mb-5 flex items-center gap-2">
          <Shield className="h-3 w-3" /> Consensus Verdicts
        </p>
        <div className="flex flex-wrap gap-3">
          {VERDICTS.map(({ icon: Icon, label, color, bg }) => (
            <div key={label} className={`flex items-center gap-2.5 rounded-lg border ${bg} px-4 py-3`}>
              <Icon className={`h-4 w-4 ${color}`} />
              <span className={`font-semibold text-sm ${color}`}>{label}</span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-zinc-500 max-w-lg">
          Weighted by validator reliability scores. Accept/reject thresholds are configurable via environment variables.
          Claims below threshold are quarantined for human review.
        </p>
      </section>

      {/* ── Agentverse ── */}
      <section className="px-8 py-10 border-b border-zinc-800/60">
        <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest mb-5 flex items-center gap-2">
          <Bot className="h-3 w-3" /> Agentverse Agent
        </p>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-5 py-4 space-y-3 max-w-2xl">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="font-semibold text-zinc-100">Quorum Validator</span>
            <Badge className="bg-emerald-950/40 text-emerald-300 border-emerald-800 text-xs">Active</Badge>
          </div>
          <p className="font-mono text-xs text-zinc-400 break-all">
            agent1qtvr2pk4hp4gfh4wh2af33vpjv5zmawz9tj4q6ngt09tandh2jg8smkfak9
          </p>
          <p className="text-xs text-zinc-500">
            Chat with this agent directly on ASI:One — send any factual claim and receive a structured verdict with per-validator breakdown.
          </p>
          <div className="pt-1">
            <code className="text-[10px] bg-zinc-800 text-zinc-300 rounded px-2 py-1 block">
              &quot;Renewable energy ETFs outperformed the S&amp;P 500 by 4% YTD.&quot;
            </code>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="px-8 py-6 flex flex-wrap items-center justify-between gap-4">
        <p className="text-xs text-zinc-600">Built on Fetch.ai uAgents · Anthropic Claude · Browserbase</p>
        <div className="flex gap-4 text-xs text-zinc-600">
          <Link href="/demo" className="hover:text-zinc-400 transition-colors">Demo</Link>
          <Link href="/trust" className="hover:text-zinc-400 transition-colors">Trust Scores</Link>
          <Link href="/quarantine" className="hover:text-zinc-400 transition-colors">Quarantine</Link>
        </div>
      </footer>
    </div>
  );
}
