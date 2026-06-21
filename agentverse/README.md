# Quorum Validator Agent

**Category:** Trust & Safety  
**Domain:** Finance / General  
**Protocol version:** QuorumValidation 1.0

## What it does

Validates any factual claim through a three-layer consensus pipeline:

| Validator | What it checks |
|---|---|
| **Source** | Web search (DuckDuckGo + Wikipedia + optional Browserbase) — does real-world evidence support the claim? |
| **Consistency** | Does the claim contradict anything already accepted in this workflow session? |
| **Reasoning** | Is the claim internally coherent? Does it make logically sound inferences? |

Returns a **consensus verdict** (`accepted` / `rejected` / `needs_review`) with a 0–1 score and per-validator rationale.

---

## How to query from ASI:One

Send a `TextValidationRequest`:

```json
{
  "statement": "Renewable energy ETFs have outperformed the S&P 500 by 4% YTD.",
  "agent_id": "your-agent-id",
  "workflow_id": "wf-your-workflow"
}
```

You will receive a `TextValidationResponse`:

```json
{
  "verdict": "accepted",
  "score": 0.74,
  "rationale": "Weighted consensus 0.74 exceeds accept threshold 0.70.",
  "validator_breakdown": [
    {"validator": "source",      "verdict": "accepted", "confidence": 0.82, "rationale": "…"},
    {"validator": "consistency", "verdict": "accepted", "confidence": 0.90, "rationale": "…"},
    {"validator": "reasoning",   "verdict": "accepted", "confidence": 0.88, "rationale": "…"}
  ]
}
```

---

## How to query from another uAgent

Include the `QuorumValidation` protocol and send a `ClaimSubmission`:

```python
from uagents import Agent, Context, Model, Protocol
from quorum.agents.protocols import ClaimSubmission, ValidationVerdict, quorum_protocol

QUORUM_ADDRESS = "agent1q..."   # this agent's address

agent = Agent(name="my-agent", seed="...")

@agent.on_interval(period=30)
async def submit(ctx: Context):
    claim_dict = {
        "id": str(uuid4()),
        "agent_id": ctx.address,
        "workflow_id": "wf-myworkflow",
        "statement": "Apple Q3 2025 revenue grew 8% YoY.",
        "payload": {},
        "created_at": datetime.utcnow().isoformat(),
    }
    await ctx.send(QUORUM_ADDRESS, ClaimSubmission(claim=claim_dict, workflow_id="wf-myworkflow"))

@agent.on_message(model=ValidationVerdict)
async def on_verdict(ctx: Context, sender: str, msg: ValidationVerdict):
    print(f"Verdict: {msg.verdict}  Score: {msg.score:.2f}")
    print(f"Rationale: {msg.rationale}")

agent.include(quorum_protocol)
agent.run()
```

---

## Verdicts explained

| Verdict | Score range | Meaning |
|---|---|---|
| `accepted` | ≥ 0.70 | Claim is well-supported — safe to act on |
| `needs_review` | 0.30 – 0.69 | Inconclusive — human review recommended |
| `rejected` | < 0.30 | Claim contradicts evidence or is logically unsound |

---

## Deployment

```bash
# Install deps
pip install -e ".[agentverse]"

# Set env vars
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and AGENTVERSE_API_KEY

# Run
python run_agentverse.py
```

The agent's address is deterministic based on `AGENT_SEED` — it stays the same across restarts.
