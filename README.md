# Quorum

**Trust and consensus layer for Fetch.ai multi-agent systems.**

> Prevents a single hallucinating agent from corrupting an entire multi-agent workflow.

---

## The Problem

When one agent produces a bad output in a Fetch.ai workflow, the error propagates through every downstream agent:

```
Weather Agent → Wrong Claim → Planner → Budget Agent → Wrong Outcome
```

Quorum intercepts every claim before it becomes canonical workflow state and runs it through three independent validators before allowing it to proceed.

---

## Architecture

```
Agent Claim
    ↓
┌─────────────────────────────────────────────┐
│               Quorum Pipeline               │
│                                             │
│  ┌────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Source │  │ Consistency │  │ Reasoning│ │
│  │  Val.  │  │    Val.     │  │   Val.   │ │
│  └────────┘  └─────────────┘  └──────────┘ │
│         ↓           ↓              ↓        │
│         └───────────┴──────────────┘        │
│                     ↓                       │
│              Consensus Engine               │
│         reliability × confidence            │
│              × evidence quality             │
│                     ↓                       │
│    ACCEPTED │ NEEDS_REVIEW │ REJECTED        │
│                     ↓                       │
│  State Store │ Quarantine │ Provenance       │
└─────────────────────────────────────────────┘
    ↓               ↓               ↓
Workflow State   Dashboard      Trust Scores
```
<img width="1774" height="887" alt="ChatGPT Image Jun 21, 2026 at 10_45_46 AM" src="https://github.com/user-attachments/assets/e138db18-219b-4967-adca-2620c4fec5b2" />

---

## Components

| Component | Description |
|---|---|
| **Source Validator** | Checks claims against OpenWeatherMap, PubMed, SEC EDGAR, Browserbase |
| **Consistency Validator** | Detects contradictions with prior accepted workflow claims via Anthropic |
| **Reasoning Validator** | Evaluates logical soundness of claims via Anthropic (with optional debate round) |
| **Consensus Engine** | Weighted scoring: `reliability × confidence × evidence_quality` |
| **Quarantine** | Holds NEEDS_REVIEW claims in `quorum:pending_claims` |
| **Provenance Layer** | Immutable audit trail: who said what, who validated it, why it was accepted |
| **Trust Manager** | Per-agent trust scores + per-validator reliability, updated after every consensus |
| **FastAPI + WS** | REST API + real-time WebSocket stream of consensus events |
| **Next.js Dashboard** | 4-page shadcn/ui dashboard: Live Consensus, Provenance, Trust, Quarantine |
| **Fetch.ai uAgents** | Quorum gatekeeper agent + weather demo workflow (Bureau) |

---

## Sponsor Alignment

| Sponsor | Usage |
|---|---|
| **Fetch.ai** | uAgents protocols, Bureau multi-agent orchestration |
| **Redis** | Workflow state, provenance, trust, quarantine, consensus history |
| **Anthropic** | Consistency + reasoning validators (Claude) |
| **Browserbase** | Web verification fallback for open-ended claims |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Redis)

### Backend

```bash
# Clone and install
git clone https://github.com/your-org/quorum
cd quorum
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Fill in API keys in .env

# Start Redis
docker-compose up redis -d

# Run tests
pytest

# Start API server
uvicorn quorum.api.main:app --reload
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

### Full stack with Docker Compose

```bash
docker-compose up
# API: http://localhost:8000
# Dashboard: http://localhost:3000
```

### Weather Demo (Fetch.ai Agents)

```bash
source .venv/bin/activate
python -m quorum.agents.demo_workflow
```

This runs the weather scenario:
1. `WeatherAgent` submits "0% chance of rain" (hallucinated)
2. Quorum validates → **REJECTED** (contradicts NOAA + reasoning failure)
3. `FallbackAgent` submits "75% rain based on NOAA" 
4. Quorum validates → **ACCEPTED**
5. `PlannerAgent` and `BudgetAgent` receive the correct forecast

---

## API Reference

See [`docs/api.md`](docs/api.md) for the full REST + WebSocket schema.

Key endpoints:

```
POST /claims/validate          — Submit a claim for validation
GET  /claims/{id}/provenance   — Audit trail for a claim
GET  /workflows/{id}/state     — Current canonical workflow state
GET  /agents/trust             — Agent trust scores
GET  /validators/reliability   — Validator reliability scores
GET  /claims/quarantine        — Quarantined (NEEDS_REVIEW) claims
WS   /stream                   — Real-time consensus event stream
```

---

## Project Structure

```
quorum/
  quorum/
    contracts/      # Shared Pydantic models, interfaces, Redis keys, config
    validators/     # source.py, consistency.py, reasoning.py
    consensus/      # engine.py, scoring.py, quarantine.py
    state/          # redis_store.py, provenance.py, trust.py
    agents/         # Fetch.ai uAgents + demo workflow
    api/            # FastAPI routes, WS, observability, startup
    fakes/          # In-memory fakes for testing
    pipeline.py     # QuorumPipeline (integration wiring)
  tests/            # 177 tests across all components
  dashboard/        # Next.js + shadcn/ui light-mode dashboard
  docs/api.md       # API schema
  docker-compose.yml
```

---

## Test Coverage

```
pytest                 # 177 tests, ~2s
pytest tests/contracts # Shared models + fakes
pytest tests/validators# Source, consistency, reasoning validators
pytest tests/consensus # Engine, scoring, quarantine
pytest tests/state     # Redis store, provenance, trust
pytest tests/agents    # uAgents protocols + quorum agent
pytest tests/api       # FastAPI routes + WebSocket
pytest tests/test_pipeline.py  # End-to-end pipeline integration
```
