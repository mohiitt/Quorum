# Quorum — Devpost Submission

---

## Inspiration

There is a silent assumption baked into almost every multi-agent AI system built today: that the agents feeding each other information are telling the truth.

They are not always.

We started thinking about this after watching a demo where a research agent confidently passed a hallucinated statistic downstream — and by the time it reached the final output layer, three more agents had cited it, reasoned from it, and built recommendations on top of it. The hallucination didn't just survive; it compounded. One wrong claim upstream behaves like an avalanche: small at the origin, catastrophic at the base.

This isn't a hypothetical edge case. It is the *default* failure mode of any pipeline where agents trust each other without verification. In financial analysis, healthcare triage, legal research, or automated decision-making — a single undetected error early in the chain can corrupt everything downstream with mathematical certainty.

We built Quorum because **multi-agent systems are only as trustworthy as their least reliable agent** — and nobody was solving that.

---

## What It Does

Quorum is a drop-in validation layer that intercepts any factual claim before it propagates through a multi-agent pipeline and returns a structured, machine-readable consensus verdict.

Every claim runs through three independent validators in parallel:

### 🌐 Source Validator — *powered by Browserbase*
The Source Validator doesn't just query an API — it *browses the web like a human researcher*. Using Browserbase's cloud browser infrastructure, it navigates live pages, extracts real content, and cross-references the claim against DuckDuckGo search results and Wikipedia. This gives us ground-truth web evidence that static APIs simply can't provide. Each source is scored for topic relevance, and the validator gracefully degrades to a benefit-of-the-doubt score when no sources are retrievable — so the pipeline never hard-crashes on network failures.

### 🔁 Consistency Validator — *powered by Redis*
The Consistency Validator maintains a live memory of every claim accepted within a workflow session, persisted in Redis. When a new claim arrives, it compares it against all prior accepted claims and surfaces contradictions — even subtle ones across different time periods, metrics, or subsectors. Redis was critical here: it gave us sub-millisecond cross-claim lookups even as workflow histories grew, and let us support concurrent sessions without state bleed. Without a fast, durable store, this validator would be unusable at any real scale.

### 🧠 Reasoning Validator — *powered by Anthropic Claude*
The Reasoning Validator asks the hardest question: *is this claim internally coherent?* Claude evaluates the logical structure of the claim — flagging unsupported conclusions, circular reasoning, category errors, and open-ended questions masquerading as factual assertions. It doesn't just check if something is *true*; it checks if it's *the kind of statement that can be evaluated as true or false* in the first place.

### Consensus Engine
The three validators vote independently. Each verdict is weighted by a reliability score and combined into a single consensus score between 0 and 1. Claims above the acceptance threshold pass. Claims below the rejection threshold are blocked. Claims in between are quarantined for human review — not silently dropped, not blindly passed.

### Fetch.ai Agentverse Integration
Quorum was built from the ground up to live in the Fetch.ai ecosystem. The agent is deployed on Agentverse with a mailbox endpoint, fully discoverable, and ships with the **Agent Chat Protocol** — meaning it can be queried directly from **ASI:One** as a first-class citizen. Any user building a multi-agent workflow on Fetch.ai can drop our agent address in and get instant validation on every claim their pipeline produces. No integration code. No custom API. Just an agent talking to an agent.

A real-time dashboard surfaces live pipeline activity: per-agent verdicts, validator breakdowns, trust scores, quarantine queue, and full provenance trails.

---

## How We Built It

**Backend:** Python, FastAPI, uAgents (Fetch.ai), asyncio  
**Validators:** Browserbase (live web), Redis (session memory), Anthropic Claude (reasoning)  
**Agentverse:** uAgents mailbox deployment, Agent Chat Protocol v0.3.0, Agentverse API registration  
**Frontend:** Next.js 15 (App Router), Tailwind CSS, shadcn/ui, WebSocket streaming  
**Infrastructure:** Redis Cloud, git-based secrets management, environment-driven validator configuration  

The architecture is deliberately modular — validators are loaded at startup based on which API keys are available, so the system degrades gracefully in constrained environments rather than failing completely. The consensus engine is decoupled from the validator implementations, so new validators can be added without touching the core pipeline logic.

---

## Challenges We Ran Into

**Redis on a public network.**
Connecting to a managed Redis instance over a public endpoint introduced latency and occasional connection drops under the async load of parallel validators. We had to implement retry logic, connection pooling, and a `FakeStore` fallback so the pipeline could continue running even if Redis became temporarily unreachable — critical for a live demo environment.

**Fetch.ai protocol spec lock.**
The Agent Chat Protocol spec in the uAgents framework locks the set of allowed `replies` at registration time. When we tried to add a `ChatAcknowledgement` handler after the fact, the protocol verification failed because the original spec didn't include it. We had to understand the internals of how `ProtocolSpecification` works, pass `replies=None` to bypass the locked reply set, and register both message handlers correctly — a non-obvious fix that took significant debugging.

**ASI:One discoverability.**
Getting the agent to actually appear in ASI:One search required more than just deploying it — the agent needed a proper name, description within the 300-character limit, and an active mailbox endpoint registered through the Agentverse API. The registration flow involved a three-step identity challenge-proof-register sequence that had to be triggered correctly at startup.

**Git secrets in commit history.**
Mid-development, our `.env` file with API keys was accidentally committed. GitHub's push protection blocked every push until the file was fully purged from git history using `git filter-branch` — which also nuked the working tree copy. We had to purge, recreate, and re-push cleanly, which cost us valuable time and reinforced a hard lesson about secrets hygiene under deadline pressure.

**Validator output formatting.**
Python enum string representations (`ValidatorName.REASONING`) leaked into frontend output and pipeline rationale text. Fixing it required patching both the backend reply formatter and the frontend rendering layer, and catching a TypeScript `s`-flag regex incompatibility along the way.

---

## Accomplishments That We're Proud Of

We built something that *works* — not just as a demo, but as a production-grade architecture that holds up under adversarial claims, network failures, and concurrent sessions.

But the accomplishment we're most proud of isn't technical.

**Quorum is deployed. Right now. On Agentverse.** Anyone building a multi-agent workflow on Fetch.ai can query our agent today — not in a future roadmap, not in a mock environment. A real agent, at a real address, returning real verdicts. That felt significant to us: not just building something cool, but shipping something *usable*.

We're also proud of the seamless ASI:One integration. The chat protocol means a non-developer can type a claim into the ASI:One interface and get back a structured, human-readable breakdown of what three independent AI systems thought about it. That's a genuinely new capability.

And on a personal level: we're proud that we kept the codebase clean, the architecture honest, and the scope disciplined — even when the temptation to add more features was constant.

---

## What We Learned

**Technical:**
- How Fetch.ai's uAgents framework handles protocol registration, identity challenges, and Agentverse mailbox routing — including the parts the documentation doesn't cover
- How to build a consensus engine that is robust to partial validator failure without sacrificing correctness
- How Browserbase's async browser sessions work at scale and how to extract structured signals from unstructured live web content
- How Redis enables stateful session memory in otherwise stateless async pipelines
- How to manage TypeScript/Next.js App Router constraints when building real-time WebSocket-driven dashboards

**Human:**
Building under a tight deadline exposed every assumption we had about how long things take. Features that look simple in a design doc have sharp edges. The things that break are never the things you tested. We learned to timebox ruthlessly, ship the imperfect version that *works* over the perfect version that doesn't exist yet, and resist the pull of scope creep when momentum feels good.

We learned how to work in parallel without stepping on each other — splitting the pipeline backend from the frontend from the Agentverse integration, then stitching them together cleanly at the end. And we learned, the hard way, that sleep is a performance-enhancing tool, not a luxury.

---

## What's Next for Quorum

The ideal future for this project isn't a standalone app — it's middleware.

The most natural integration point is **Fetch.ai's internal orchestration layer**. When an AI system decides to spin up a multi-agent workflow — research agents, analysis agents, decision agents — Quorum sits in the middle, validating the signal as it flows between them. Not as an optional plugin. As a standard component. The way a load balancer sits between a client and a server not because anything is broken, but because you don't run production systems without one.

We'd want to work with Fetch.ai to embed Quorum into the default scaffolding for multi-agent pipelines on ASI:One — so that any workflow built on the platform has trust and consensus built in from day one, not bolted on after the first incident.

Beyond that: expanding the validator set (financial data APIs, scientific literature, live news feeds), adding configurable trust profiles per workflow domain, and building a provenance graph that lets operators trace exactly *which* upstream claim was the origin of a downstream error.

The goal isn't to make AI agents perfect. It's to make their failures visible, bounded, and recoverable.

---

*Built with Fetch.ai uAgents · Anthropic Claude · Browserbase · Redis · Next.js*
