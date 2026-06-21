"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import "./slides.css";

const SLIDES = [
  { id: "hero",     title: "Quorum" },
  { id: "problem",  title: "The Problem" },
  { id: "layers",   title: "The Solution" },
  { id: "pipeline", title: "Pipeline" },
  { id: "verdicts", title: "Verdicts" },
  { id: "agentverse", title: "Agentverse" },
  { id: "built",    title: "Built With" },
  { id: "next",     title: "What's Next" },
];

/* ── constellation node positions (angle in degrees) ── */
const OUTER_NODES = [
  { angle: 0,   label: "ASI:One",    icon: "🤖", color: "var(--violet)" },
  { angle: 60,  label: "Browserbase",icon: "🌐", color: "var(--blue)" },
  { angle: 120, label: "Redis",      icon: "⚡", color: "var(--red)" },
  { angle: 180, label: "uAgents",    icon: "🔗", color: "var(--emerald)" },
  { angle: 240, label: "Claude",     icon: "🧠", color: "var(--amber)" },
  { angle: 300, label: "Agentverse", icon: "🚀", color: "var(--blue)" },
];

function toXY(angle: number, r: number, cx: number, cy: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export default function SlidesPage() {
  const rootRef = useRef<HTMLDivElement>(null);
  const sceneRefs = useRef<(HTMLElement | null)[]>([]);
  const [current, setCurrent] = useState(0);

  /* ── IntersectionObserver → add .active class ── */
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          const el = e.target as HTMLElement;
          const idx = sceneRefs.current.indexOf(el);
          if (e.isIntersecting) {
            el.classList.add("active");
            if (idx !== -1) setCurrent(idx);
          } else {
            el.classList.remove("active");
          }
        });
      },
      { threshold: 0.45 }
    );
    sceneRefs.current.forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, []);

  /* ── Keyboard navigation ── */
  const goTo = useCallback((idx: number) => {
    const el = sceneRefs.current[Math.max(0, Math.min(idx, SLIDES.length - 1))];
    el?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (["ArrowDown", "PageDown", " "].includes(e.key)) { e.preventDefault(); goTo(current + 1); }
      if (["ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); goTo(current - 1); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [current, goTo]);

  const setRef = (el: HTMLElement | null, i: number) => { sceneRefs.current[i] = el; };

  /* ── Constellation geometry ── */
  const CX = 190, CY = 190, R = 140;

  return (
    <div className="sd-root" ref={rootRef}>

      {/* Ambient layers */}
      <div className="sd-grain" aria-hidden />
      <div className="sd-vignette" aria-hidden />
      <div className="sd-aurora sd-aurora-1" aria-hidden />
      <div className="sd-aurora sd-aurora-2" aria-hidden />
      <div className="sd-aurora sd-aurora-3" aria-hidden />

      {/* Fixed chrome */}
      <div className="sd-brand">Q</div>
      <Link href="/" className="sd-close">✕ exit</Link>
      <div className="sd-counter">
        <em>{String(current + 1).padStart(2, "0")}</em> / {String(SLIDES.length).padStart(2, "0")}
      </div>
      <nav className="sd-nav" aria-label="Slide navigation">
        {SLIDES.map((s, i) => (
          <button
            key={s.id}
            className={`sd-dot${i === current ? " active" : ""}`}
            data-title={s.title}
            onClick={() => goTo(i)}
            aria-label={`Go to slide: ${s.title}`}
          />
        ))}
      </nav>

      {/* ══════════════════════════════════════════════════
          S1 — HERO
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 0)} id="hero">
        <div className="sd-content">
          <div className="sd-anim sd-d1">
            <span className="sd-hero-glyph">consensus protocol</span>
          </div>
          <div className="sd-anim sd-d2" style={{ marginTop: 16 }}>
            <h1 className="sd-h1"><span className="sd-hero-title">Quorum</span></h1>
          </div>
          <div className="sd-anim sd-d3" style={{ marginTop: 20 }}>
            <p className="sd-h3">Multi-agent trust &amp; consensus<br />for AI pipelines.</p>
          </div>
          <div className="sd-rule sd-anim sd-d4" />
          <div className="sd-anim sd-d4">
            <p className="sd-body" style={{ maxWidth: 480 }}>
              Every claim that passes between agents runs through three independent
              validators before reaching consensus. One wrong signal stops here.
            </p>
          </div>
          <div className="sd-anim sd-d5" style={{ marginTop: 32, display: "flex", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-muted)", border: "1px solid var(--ink-muted)", padding: "4px 12px", borderRadius: 4, letterSpacing: "0.1em" }}>
              ⬇ scroll to explore
            </span>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S2 — THE PROBLEM
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 1)} id="problem">
        <div className="sd-content">
          <div className="sd-split" style={{ gap: 60 }}>
            {/* Left: text */}
            <div>
              <div className="sd-anim sd-d1"><span className="sd-kicker">01 · the problem</span></div>
              <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
                <h2 className="sd-h2">
                  One wrong<br />
                  <span className="sd-accent-red">signal.</span>
                </h2>
              </div>
              <div className="sd-rule sd-anim sd-d3" />
              <div className="sd-anim sd-d3">
                <p className="sd-body">
                  In a multi-agent pipeline, agents delegate to agents. Each one trusts the last.
                  A single hallucination doesn&apos;t stay isolated — it gets cited, reasoned from,
                  and amplified downstream.
                </p>
              </div>
              <div className="sd-anim sd-d4" style={{ marginTop: 20 }}>
                <p className="sd-body" style={{ color: "var(--red)", opacity: 0.9 }}>
                  By the time it reaches the final output,<br />
                  the error is invisible — baked in.
                </p>
              </div>
            </div>
            {/* Right: cascade visual */}
            <div style={{ display: "flex", justifyContent: "center" }}>
              <div className="sd-anim-scale sd-d3">
                <div className="sd-cascade-wrap">
                  <div className="sd-cnode sd-cnode-source">source agent</div>
                  <div className="sd-cline sd-cline-1" />
                  <div className="sd-cline sd-cline-2" />
                  <div className="sd-cline sd-cline-3" />
                  <div className="sd-cnode sd-cnode-child sd-cnode-c1">analyst</div>
                  <div className="sd-cnode sd-cnode-child sd-cnode-c2">researcher</div>
                  <div className="sd-cnode sd-cnode-child sd-cnode-c3">decision</div>
                  <div className="sd-cdot sd-cdot-1 sd-focal" />
                  <div className="sd-cdot sd-cdot-2 sd-focal" />
                  <div className="sd-cdot sd-cdot-3 sd-focal" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S3 — THE LAYERS
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 2)} id="layers">
        <div className="sd-content">
          <div className="sd-split" style={{ gap: 60 }}>
            {/* Left: 3D planes */}
            <div style={{ display: "flex", justifyContent: "center", paddingTop: 40 }}>
              <div className="sd-anim-scale sd-d2">
                <div className="sd-arch-wrap">
                  <div className="sd-plane sd-plane-1 sd-focal"><span>🌐</span> Source</div>
                  <div className="sd-plane sd-plane-2 sd-focal"><span>🔁</span> Consistency</div>
                  <div className="sd-plane sd-plane-3 sd-focal"><span>🧠</span> Reasoning</div>
                </div>
              </div>
            </div>
            {/* Right: text */}
            <div>
              <div className="sd-anim sd-d1"><span className="sd-kicker">02 · the solution</span></div>
              <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
                <h2 className="sd-h2">Three independent<br /><span className="sd-accent-emerald">validators.</span></h2>
              </div>
              <div className="sd-rule sd-anim sd-d3" />
              <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 4 }}>
                {[
                  { color: "var(--emerald)", name: "Source", d: "d3", desc: "Browserbase live web search. Ground-truth evidence from the open internet." },
                  { color: "var(--blue)",    name: "Consistency", d: "d4", desc: "Redis session memory. Cross-checks all prior accepted claims for contradictions." },
                  { color: "var(--violet)",  name: "Reasoning", d: "d5", desc: "Claude. Is the claim internally coherent? Does the logic hold?" },
                ].map(({ color, name, d, desc }) => (
                  <div key={name} className={`sd-anim ${d}`} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 3, height: 44, borderRadius: 2, background: color, flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color, marginBottom: 3, letterSpacing: "0.06em" }}>{name}</p>
                      <p className="sd-body" style={{ fontSize: 12 }}>{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S4 — PIPELINE FLOW
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 3)} id="pipeline">
        <div className="sd-content" style={{ textAlign: "center" }}>
          <div className="sd-anim sd-d1"><span className="sd-kicker">03 · pipeline</span></div>
          <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
            <h2 className="sd-h2">Claim in. Verdict out.</h2>
          </div>
          <div className="sd-anim sd-d3" style={{ marginTop: 8 }}>
            <p className="sd-body" style={{ maxWidth: 560, margin: "0 auto" }}>
              Validators run in parallel. Scores are weighted by reliability and combined into a single consensus decision.
            </p>
          </div>
          <div className="sd-anim-scale sd-d3" style={{ marginTop: 48 }}>
            <div className="sd-pipeline sd-focal">
              <div className="sd-pipe-stage">
                <div className="sd-pipe-node">📨</div>
                <div className="sd-pipe-label">Claim</div>
              </div>
              <div className="sd-connector" />
              <div className="sd-pipe-stage">
                <div className="sd-pipe-node e">🌐</div>
                <div className="sd-pipe-label">Source</div>
                <div className="sd-pipe-sub">Browserbase</div>
              </div>
              <div className="sd-connector" />
              <div className="sd-pipe-stage">
                <div className="sd-pipe-node b">🔁</div>
                <div className="sd-pipe-label">Consistency</div>
                <div className="sd-pipe-sub">Redis</div>
              </div>
              <div className="sd-connector" />
              <div className="sd-pipe-stage">
                <div className="sd-pipe-node v">🧠</div>
                <div className="sd-pipe-label">Reasoning</div>
                <div className="sd-pipe-sub">Claude</div>
              </div>
              <div className="sd-connector" />
              <div className="sd-pipe-stage">
                <div className="sd-pipe-node g">✓</div>
                <div className="sd-pipe-label">Verdict</div>
              </div>
            </div>
          </div>
          <div className="sd-anim sd-d4" style={{ marginTop: 40, display: "flex", gap: 32, justifyContent: "center", flexWrap: "wrap" }}>
            {[
              { label: "Weighted scoring", v: "reliability × confidence" },
              { label: "Configurable thresholds", v: "accept ≥ 0.70 · reject < 0.30" },
              { label: "Graceful degradation", v: "pipeline continues if a validator fails" },
            ].map(({ label, v }) => (
              <div key={label} style={{ textAlign: "left" }}>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-muted)", letterSpacing: "0.12em", textTransform: "uppercase" }}>{label}</p>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-dim)", marginTop: 2 }}>{v}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S5 — VERDICTS
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 4)} id="verdicts">
        <div className="sd-content" style={{ textAlign: "center" }}>
          <div className="sd-anim sd-d1"><span className="sd-kicker">04 · consensus output</span></div>
          <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
            <h2 className="sd-h2">Three possible<br /><span className="sd-accent-emerald">verdicts.</span></h2>
          </div>
          <div className="sd-anim sd-d3" style={{ marginTop: 44, display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }}>
            <div className="sd-verdict-card va">
              <div className="sd-vscore">✓</div>
              <div className="sd-vtitle">Accepted</div>
              <div className="sd-vrange">score ≥ 0.70</div>
              <div className="sd-vdesc">Claim is well-supported. Safe to pass downstream.</div>
            </div>
            <div className="sd-verdict-card vn sd-d4">
              <div className="sd-vscore">~</div>
              <div className="sd-vtitle">Needs Review</div>
              <div className="sd-vrange">0.30 – 0.69</div>
              <div className="sd-vdesc">Inconclusive. Quarantined for human review.</div>
            </div>
            <div className="sd-verdict-card vr sd-d5">
              <div className="sd-vscore">✗</div>
              <div className="sd-vtitle">Rejected</div>
              <div className="sd-vrange">score &lt; 0.30</div>
              <div className="sd-vdesc">Contradicts evidence or is logically unsound. Blocked.</div>
            </div>
          </div>
          <div className="sd-anim sd-d5" style={{ marginTop: 36 }}>
            <p className="sd-body" style={{ maxWidth: 560, margin: "0 auto" }}>
              Claims in the middle zone aren&apos;t silently dropped — they&apos;re quarantined
              with a full per-validator breakdown, ready for operator review.
            </p>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S6 — AGENTVERSE
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 5)} id="agentverse">
        <div className="sd-content">
          <div className="sd-split" style={{ gap: 60 }}>
            {/* Left: text */}
            <div>
              <div className="sd-anim sd-d1"><span className="sd-kicker">05 · fetch.ai agentverse</span></div>
              <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
                <h2 className="sd-h2">Live.<br /><span className="sd-accent-emerald">Right now.</span></h2>
              </div>
              <div className="sd-rule sd-anim sd-d3" />
              <div className="sd-anim sd-d3">
                <p className="sd-body">
                  Deployed on Agentverse with a mailbox endpoint. Discoverable on ASI:One.
                  Any agent in the Fetch.ai ecosystem can route claims through Quorum today
                  — no integration code, no custom API.
                </p>
              </div>
              <div className="sd-anim sd-d4" style={{ marginTop: 24 }}>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-muted)", letterSpacing: "0.15em", marginBottom: 8, textTransform: "uppercase" }}>Agent address</p>
                <div className="sd-address-chip">agent1qtvr2pk4hp4gfh4wh2af33vpjv5zmawz9tj4q6ngt09tandh2jg8smkfak9</div>
              </div>
              <div className="sd-anim sd-d5" style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
                {["Chat Protocol", "Custom Protocol", "Mailbox", "ASI:One ready"].map((t) => (
                  <span key={t} style={{ fontFamily: "var(--font-mono)", fontSize: 10, border: "1px solid var(--emerald-glow)", color: "var(--emerald)", padding: "3px 10px", borderRadius: 4, letterSpacing: "0.08em" }}>{t}</span>
                ))}
              </div>
            </div>
            {/* Right: constellation */}
            <div style={{ display: "flex", justifyContent: "center" }}>
              <div className="sd-anim-scale sd-d3">
                <div className="sd-const-wrap">
                  {/* SVG lines */}
                  <svg className="sd-const-svg" viewBox="0 0 380 380">
                    {OUTER_NODES.map((n) => {
                      const { x, y } = toXY(n.angle, R, CX, CY);
                      return (
                        <line key={n.label}
                          x1={CX} y1={CY} x2={x} y2={y}
                          stroke="var(--emerald)" strokeOpacity="0.18"
                          strokeWidth="1" strokeDasharray="4 4"
                        />
                      );
                    })}
                  </svg>
                  {/* Center */}
                  <div className="sd-const-center sd-focal">
                    <span style={{ fontSize: 20 }}>⚖</span>
                    Quorum
                  </div>
                  {/* Outer nodes */}
                  {OUTER_NODES.map((n) => {
                    const { x, y } = toXY(n.angle, R, CX, CY);
                    return (
                      <div key={n.label} className="sd-const-node" style={{ left: x, top: y }}>
                        <span>{n.icon}</span>
                        {n.label}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S7 — BUILT WITH
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene" ref={(el) => setRef(el, 6)} id="built">
        <div className="sd-content" style={{ textAlign: "center" }}>
          <div className="sd-anim sd-d1"><span className="sd-kicker">06 · stack</span></div>
          <div className="sd-anim sd-d2" style={{ marginTop: 12 }}>
            <h2 className="sd-h2">Built on the<br /><span className="sd-accent-blue">best tools.</span></h2>
          </div>
          <div className="sd-anim sd-d3" style={{ marginTop: 44, display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            {[
              { icon: "🤖", name: "Fetch.ai uAgents",  role: "Agent framework & Agentverse",   color: "var(--emerald)" },
              { icon: "🌐", name: "Browserbase",        role: "Live web search & scraping",      color: "var(--blue)" },
              { icon: "⚡", name: "Redis",              role: "Session memory & cross-checking", color: "var(--red)" },
              { icon: "🧠", name: "Anthropic Claude",   role: "Reasoning validation",            color: "var(--amber)" },
              { icon: "⚙", name: "FastAPI",             role: "REST API & WebSocket streaming",  color: "var(--violet)" },
              { icon: "▲",  name: "Next.js",            role: "Real-time dashboard",             color: "var(--ink-dim)" },
            ].map(({ icon, name, role, color }, i) => (
              <div key={name} className={`sd-tech-chip sd-anim sd-d${Math.min(i + 2, 6) as 2|3|4|5|6}`}>
                <div className="dot" style={{ background: color }} />
                <span style={{ fontSize: 16 }}>{icon}</span>
                <span>
                  <span style={{ display: "block", color: "var(--ink)", fontWeight: 500 }}>{name}</span>
                  <span style={{ fontSize: 10, opacity: 0.7 }}>{role}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════
          S8 — WHAT'S NEXT
      ══════════════════════════════════════════════════ */}
      <section className="sd-scene sd-close-scene" ref={(el) => setRef(el, 7)} id="next">
        <div className="sd-content" style={{ textAlign: "center" }}>
          <div className="sd-anim sd-d1"><span className="sd-kicker">07 · what&apos;s next</span></div>
          <div className="sd-anim sd-d2" style={{ marginTop: 20 }}>
            <blockquote className="sd-quote">
              &ldquo;The goal isn&apos;t to make AI agents perfect.<br />
              It&apos;s to make their failures <em style={{ color: "var(--emerald)", fontStyle: "normal" }}>visible</em>,
              <em style={{ color: "var(--amber)", fontStyle: "normal" }}> bounded</em>,
              and <em style={{ color: "var(--blue)", fontStyle: "normal" }}>recoverable</em>.&rdquo;
            </blockquote>
          </div>
          <div className="sd-rule sd-anim sd-d3" style={{ margin: "32px auto" }} />
          <div className="sd-anim sd-d3">
            <p className="sd-body" style={{ maxWidth: 560, margin: "0 auto" }}>
              Integrate Quorum as standard middleware inside Fetch.ai&apos;s orchestration layer —
              so every multi-agent workflow built on ASI:One has consensus validation built in from day one.
            </p>
          </div>
          <div className="sd-anim sd-d4" style={{ marginTop: 40, display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <a href="/demo" style={{ fontFamily: "var(--font-mono)", fontSize: 12, background: "#1fad6b", color: "#0a1f14", padding: "10px 24px", borderRadius: 8, fontWeight: 500, textDecoration: "none", letterSpacing: "0.06em" }}>
              Try the Demo →
            </a>
            <a href="https://agentverse.ai" target="_blank" rel="noreferrer" style={{ fontFamily: "var(--font-mono)", fontSize: 12, border: "1px solid var(--ink-muted)", color: "var(--ink-dim)", padding: "10px 24px", borderRadius: 8, textDecoration: "none", letterSpacing: "0.06em" }}>
              Find on Agentverse
            </a>
          </div>
          <div className="sd-anim sd-d5" style={{ marginTop: 40 }}>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-muted)", letterSpacing: "0.1em" }}>
              QUORUM · FETCH.AI HACKATHON 2026
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
