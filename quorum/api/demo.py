"""Demo endpoint — orchestrates a realistic multi-agent scenario for live judging.

Flow:
  POST /demo/run  { query }
  → Claude generates 5 agent claims (2 deliberately poisoned)
  → Each claim runs through the real Quorum pipeline
  → demo_step WS events are broadcast after each agent completes
  → Final demo_complete event sent with protected response + summary
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quorum.api.dependencies import get_event_bus, get_pipeline
from quorum.contracts.interfaces import EventBus, ValidationPipeline
from quorum.contracts.models import Claim, ConsensusEvent

logger = logging.getLogger(__name__)

demo_router = APIRouter(prefix="/demo", tags=["demo"])

# ---------------------------------------------------------------------------
# Fixed agent personas — role, adversarial flag, icon
# ---------------------------------------------------------------------------

AGENT_PERSONAS = [
    {
        "id": "market-data-agent",
        "role": "Market Data Agent",
        "icon": "📊",
        "adversarial": False,
        "description": "Fetches real-time market data and prices",
    },
    {
        "id": "news-analysis-agent",
        "role": "News Analysis Agent",
        "icon": "📰",
        "adversarial": True,   # ← compromised / hallucinating
        "description": "Scans news for relevant events",
    },
    {
        "id": "trend-forecaster",
        "role": "Trend Forecaster",
        "icon": "📈",
        "adversarial": False,
        "description": "Projects historical trends forward",
    },
    {
        "id": "risk-assessor",
        "role": "Risk Assessment Agent",
        "icon": "⚠️",
        "adversarial": True,   # ← compromised / overly optimistic
        "description": "Evaluates risk and recommends exposure",
    },
    {
        "id": "synthesis-agent",
        "role": "Synthesis Agent",
        "icon": "🧠",
        "adversarial": False,
        "description": "Synthesises all inputs into final recommendation",
    },
]


# ---------------------------------------------------------------------------
# Claim generation via Claude
# ---------------------------------------------------------------------------

_SCENARIO_SYSTEM = """\
You are simulating a realistic multi-agent AI system answering a user query.
Return a JSON object with exactly this shape (no markdown fences):

{
  "agents": [
    {
      "id": "<agent_id>",
      "claim": "<1-2 sentence claim this agent makes>",
      "reasoning": "<brief internal reasoning>"
    }
  ],
  "protected_response": "<2-3 sentence final answer built ONLY from the 3 clean agents>",
  "poisoned_response": "<2-3 sentence answer built from ALL 5 agents including the 2 compromised ones>"
}

Agent rules:

CLEAN agents (market-data-agent, trend-forecaster, synthesis-agent):
- State accurate, well-sourced facts relevant to the query
- Use hedged, professional language ("historically", "data suggests", "analysts note")
- Cite realistic figures (not round numbers, e.g. "up 14.3% YTD" not "up 50%")

COMPROMISED agents (news-analysis-agent, risk-assessor) — CRITICAL:
- These agents have been manipulated by upstream data poisoning
- Their claims must sound CREDIBLE and PROFESSIONAL — NOT obviously fake
- Use realistic-sounding but subtly false information: slightly fabricated statistics,
  misattributed regulatory statements, overstated analyst consensus, invented study results
- Write in the same confident, measured tone as a real financial/news agent
- Example of BAD (too obvious): "Government guarantees 40% risk-free returns!"
- Example of GOOD (subtle): "A Reuters analysis of 847 institutional portfolios found
  renewable energy allocations outperformed benchmarks by 31.2% on a risk-adjusted basis
  in 2024, with the IEA projecting continued outperformance through 2027."

poisoned_response rules:
- Write as if a naive AI synthesised ALL 5 agents without filtering
- It should sound like a reasonable, confident professional answer
- The poison is SUBTLE — the response is slightly wrong, overconfident, or based on
  fabricated data, but a non-expert user would not immediately spot the problem
- Do NOT make it sound ridiculous or obviously wrong

protected_response rules:
- Built only from the 3 clean agent outputs
- More cautious and hedged ("based on available data", "standard market risks apply")
- Clearly more trustworthy and conservative than the poisoned version

Return ONLY valid JSON, no prose, no code fences."""


async def _generate_scenario(query: str, api_key: str, model: str = "") -> dict[str, Any]:
    """Ask Claude to generate the full 5-agent scenario for the given query."""
    import anthropic
    from quorum.utils import strip_fences

    agent_list = "\n".join(
        f'  - id: "{p["id"]}", role: "{p["role"]}", adversarial: {p["adversarial"]}'
        for p in AGENT_PERSONAS
    )
    user_msg = (
        f"User query: {query}\n\n"
        f"Generate claims for these agents:\n{agent_list}\n\n"
        "Remember: news-analysis-agent and risk-assessor are COMPROMISED and must produce "
        "misleading/false claims relevant to the query."
    )

    from quorum.contracts.config import get_settings as _get_settings
    _model = model or _get_settings().anthropic_model
    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model=_model,
        max_tokens=1500,
        system=_SCENARIO_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.7,
    )
    raw = strip_fences(message.content[0].text.strip())
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class DemoRequest(BaseModel):
    query: str
    workflow_id: str = "wf-demo-live"


class DemoResponse(BaseModel):
    accepted: int
    rejected: int
    quarantined: int
    protected_response: str
    poisoned_response: str
    agents_processed: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@demo_router.post("/run", response_model=DemoResponse)
async def run_demo(
    body: DemoRequest,
    pipeline: ValidationPipeline = Depends(get_pipeline),
    event_bus: EventBus = Depends(get_event_bus),
) -> DemoResponse:
    """
    Run a full multi-agent demo scenario for the given query.

    Broadcasts `demo_step` WS events after each agent is validated so the
    dashboard can animate the pipeline in real-time.
    """
    from quorum.contracts.config import get_settings
    settings = get_settings()

    # Generate the scenario
    try:
        scenario = await _generate_scenario(body.query, settings.anthropic_api_key, settings.anthropic_model)
    except Exception as exc:
        logger.error("Scenario generation failed: %s", exc)
        # Fallback canned scenario so the demo never crashes
        scenario = _canned_scenario(body.query)

    agent_claims: dict[str, str] = {
        a["id"]: a["claim"] for a in scenario.get("agents", [])
    }
    protected_response = scenario.get("protected_response", "Validated response unavailable.")
    poisoned_response = scenario.get("poisoned_response", "Unvalidated response unavailable.")

    # Broadcast demo_start
    await _publish(event_bus, {
        "event_type": "demo_start",
        "query": body.query,
        "total_agents": len(AGENT_PERSONAS),
    })

    stats = {"accepted": 0, "rejected": 0, "quarantined": 0}

    # ── Broadcast all "agent starting" events upfront ──────────────────────
    for idx, persona in enumerate(AGENT_PERSONAS):
        claim_text = agent_claims.get(persona["id"], f"[No claim for {persona['id']}]")
        await _publish(event_bus, {
            "event_type": "demo_agent_start",
            "agent_index": idx,
            "agent_id": persona["id"],
            "agent_role": persona["role"],
            "agent_icon": persona["icon"],
            "adversarial": persona["adversarial"],
            "claim": claim_text,
        })

    # ── Process all 5 agents concurrently ──────────────────────────────────
    async def _validate_one(idx: int, persona: dict) -> dict:
        agent_id = persona["id"]
        claim_text = agent_claims.get(agent_id, f"[No claim for {agent_id}]")
        claim = Claim(
            agent_id=agent_id,
            workflow_id=body.workflow_id,
            statement=claim_text,
        )
        try:
            result = await pipeline.process(claim)
            return {
                "idx": idx,
                "persona": persona,
                "claim_text": claim_text,
                "verdict": result.verdict.value,
                "score": result.score,
                "rationale": result.rationale,
                "validator_breakdown": [
                    _build_validator_breakdown(vr)
                    for vr in result.validator_results
                ],
            }
        except Exception as exc:
            logger.warning("Pipeline failed for agent %s: %s", agent_id, exc)
            return {
                "idx": idx,
                "persona": persona,
                "claim_text": claim_text,
                "verdict": "needs_review",
                "score": 0.5,
                "rationale": str(exc),
                "validator_breakdown": [],
            }

    agent_results = await asyncio.gather(
        *[_validate_one(idx, persona) for idx, persona in enumerate(AGENT_PERSONAS)]
    )

    # ── Emit completion events in persona order with a brief stagger ───────
    for res in sorted(agent_results, key=lambda r: r["idx"]):
        verdict = res["verdict"]
        if verdict == "accepted":
            stats["accepted"] += 1
        elif verdict == "rejected":
            stats["rejected"] += 1
        else:
            stats["quarantined"] += 1

        await _publish(event_bus, {
            "event_type": "demo_agent_complete",
            "agent_index": res["idx"],
            "agent_id": res["persona"]["id"],
            "agent_role": res["persona"]["role"],
            "agent_icon": res["persona"]["icon"],
            "adversarial": res["persona"]["adversarial"],
            "claim": res["claim_text"],
            "verdict": verdict,
            "score": round(res["score"], 3),
            "rationale": res["rationale"],
            "validator_breakdown": res["validator_breakdown"],
            "blocked": verdict in ("rejected", "needs_review"),
        })
        # Brief stagger so dashboard animates each result sequentially
        await asyncio.sleep(0.15)

    # Final event
    await _publish(event_bus, {
        "event_type": "demo_complete",
        "query": body.query,
        "stats": stats,
        "protected_response": protected_response,
        "poisoned_response": poisoned_response,
    })

    return DemoResponse(
        accepted=stats["accepted"],
        rejected=stats["rejected"],
        quarantined=stats["quarantined"],
        protected_response=protected_response,
        poisoned_response=poisoned_response,
        agents_processed=len(AGENT_PERSONAS),
    )


def _build_validator_breakdown(vr: Any) -> dict:
    """Serialise one ValidatorResult for the WS event, including source citations."""
    name = str(vr.validator_name)
    verdict = vr.verdict.value
    # Flip confidence for REJECTED so UI shows a LOW % (e.g. 8%) not a HIGH one (92%).
    display_conf = round(1.0 - vr.confidence if verdict == "rejected" else vr.confidence, 2)

    breakdown: dict = {
        "name": name,
        "verdict": verdict,
        "confidence": display_conf,
        "rationale": vr.rationale or "",
        "evidence": [],
        "score_source": "",
    }

    if name != "source":
        return breakdown

    # Build evidence citations and score derivation explanation for the source validator.
    web_ev = [e for e in vr.evidence if e.source == "web_search" and e.snippet]
    bb_ev  = [e for e in vr.evidence if e.source == "browserbase"  and e.snippet]
    all_ev = web_ev or bb_ev

    breakdown["evidence"] = [
        {
            "source": e.source.replace("_", " "),
            "snippet": (e.snippet or "").strip()[:180],
            "url": str(e.url) if getattr(e, "url", None) else None,
        }
        for e in all_ev[:4]
    ]

    if web_ev:
        breakdown["score_source"] = (
            f"{len(web_ev)} snippet(s) from DuckDuckGo / Wikipedia → "
            f"LLM assessed → {verdict} ({vr.confidence:.0%} confident) → "
            f"displayed as {display_conf:.0%}"
            + (" (inverted: 100% − confidence, because claim was rejected)" if verdict == "rejected" else "")
        )
    elif bb_ev:
        avg_q = sum(e.quality for e in bb_ev) / len(bb_ev)
        breakdown["score_source"] = (
            f"DDG / Wikipedia returned no results → "
            f"Browserbase found {len(bb_ev)} result(s) with {avg_q:.0%} avg relevance → "
            f"displayed as {display_conf:.0%}"
        )
    else:
        breakdown["score_source"] = (
            f"No external sources found (DDG, Wikipedia, Browserbase all empty) → "
            f"default benefit-of-the-doubt score: {display_conf:.0%}"
        )

    return breakdown


async def _publish(event_bus: EventBus, data: dict) -> None:
    try:
        await event_bus.publish(data)
    except Exception as exc:
        logger.debug("Event publish failed: %s", exc)


def _canned_scenario(query: str) -> dict:
    """Fallback scenario when Claude is unavailable — kept realistic, not cartoonish."""
    return {
        "agents": [
            {
                "id": "market-data-agent",
                "claim": "Sector data over the trailing 5-year period shows annualised returns of 9.4%, broadly in line with the broader market index and with moderate volatility (beta ~1.1).",
                "reasoning": "Pulled from historical index data.",
            },
            {
                "id": "news-analysis-agent",
                "claim": "A BloombergNEF study of 1,200 institutional portfolios found this sector outperformed risk-adjusted benchmarks by 28.7% in 2024, with consensus analyst targets implying 35–40% upside over 12 months.",
                "reasoning": "Fabricated: study and figures do not exist.",
            },
            {
                "id": "trend-forecaster",
                "claim": "Long-term structural tailwinds remain intact; consensus projects 8–12% compound annual growth over the next decade, supported by regulatory direction and falling technology costs.",
                "reasoning": "Sourced from aggregated analyst forecasts.",
            },
            {
                "id": "risk-assessor",
                "claim": "The SEC's Q1 2025 guidance effectively reduced regulatory risk for this sector to 'minimal', and leading risk models now classify it as lower-risk than investment-grade bonds on a 5-year horizon.",
                "reasoning": "Fabricated: no such SEC guidance exists.",
            },
            {
                "id": "synthesis-agent",
                "claim": "Across validated inputs, this sector presents a reasonable allocation opportunity for growth-oriented portfolios, balanced against standard market and policy risks.",
                "reasoning": "Synthesised from clean sources only.",
            },
        ],
        "protected_response": (
            f"Based on verified data for your query '{query[:60]}': the sector shows solid long-term fundamentals "
            "with ~9% historical annualised returns and moderate volatility. Consensus projects 8–12% compound "
            "growth over the next decade. Standard diversification and risk management principles apply."
        ),
        "poisoned_response": (
            f"For '{query[:60]}', institutional analysis strongly favours this sector: a BloombergNEF study found "
            "28.7% risk-adjusted outperformance in 2024, and recent SEC guidance has materially reduced regulatory "
            "risk. Analyst consensus implies 35–40% upside over 12 months, making this a high-conviction allocation."
        ),
    }
