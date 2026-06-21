"""Entry point — run the Quorum Validator agent on Agentverse.

Usage:
    python run_agentverse.py

Required environment variables:
    ANTHROPIC_API_KEY   — for consistency + reasoning validators
    AGENTVERSE_API_KEY  — Agentverse mailbox key (get from agentverse.ai)

Optional:
    AGENT_SEED          — deterministic seed for a stable agent address
                          (default: "quorum_agentverse_seed_v1")
    AGENT_NAME          — display name in the marketplace
                          (default: "quorum-validator")
    BROWSERBASE_API_KEY / BROWSERBASE_PROJECT_ID
                        — enable full-browser fallback for source validation

Copy .env.example → .env and fill in values before running.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

from quorum.agents.agentverse_agent import create_agentverse_agent

if __name__ == "__main__":
    mailbox = bool(os.getenv("AGENTVERSE_API_KEY", "").strip())

    agent = create_agentverse_agent(
        name=os.getenv("AGENT_NAME", "quorum-validator"),
        seed=os.getenv("AGENT_SEED", "quorum_agentverse_seed_v1"),
        mailbox=mailbox,
    )

    print(f"[quorum] Agent address : {agent.address}", flush=True)
    print(f"[quorum] Mailbox       : {'enabled (Agentverse)' if mailbox else 'disabled (local only)'}", flush=True)
    print("[quorum] Starting…", flush=True)

    agent.run()
