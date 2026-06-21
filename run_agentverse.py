"""Entry point — run the Quorum Validator agent on Agentverse.

Usage:
    python run_agentverse.py

Required environment variables:
    ANTHROPIC_API_KEY   — for consistency + reasoning validators
    AGENTVERSE_API_KEY  — Agentverse API key (get from agentverse.ai → My Agents → API Keys)

Optional:
    AGENT_SEED          — deterministic seed for a stable agent address
                          (default: "quorum_agentverse_seed_v1")
    AGENT_NAME          — display name in the marketplace
                          (default: "quorum-validator")
    AGENT_PORT          — local port for the agent's HTTP server (default: 8001)
    BROWSERBASE_API_KEY / BROWSERBASE_PROJECT_ID
                        — enable full-browser fallback for source validation

Copy .env.example → .env and fill in values before running.
"""

from __future__ import annotations

import logging
import os
import threading
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

from quorum.agents.agentverse_agent import create_agentverse_agent

_STARTUP_DELAY = 5  # seconds to wait for agent HTTP server to come up


def _register_on_agentverse(port: int, api_key: str) -> None:
    """Background thread: wait for agent to start, then POST to /connect."""
    time.sleep(_STARTUP_DELAY)
    url = f"http://localhost:{port}/connect"
    try:
        resp = httpx.post(
            url,
            json={"user_token": api_key, "agent_type": "uagent"},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                print("\n[quorum] ✓ Successfully registered on Agentverse!", flush=True)
                print("[quorum]   Agent is now reachable from ASI:One and other uAgents.", flush=True)
            else:
                print(f"\n[quorum] ✗ Agentverse registration failed: {data.get('detail', 'unknown')}", flush=True)
                print(f"[quorum]   Open http://localhost:{port} to register manually.", flush=True)
        else:
            print(f"\n[quorum] ✗ /connect returned HTTP {resp.status_code}", flush=True)
            print(f"[quorum]   Open http://localhost:{port} to register manually.", flush=True)
    except Exception as exc:
        print(f"\n[quorum] ✗ Auto-registration error: {exc}", flush=True)
        print(f"[quorum]   Open http://localhost:{port} to register via Agent Inspector.", flush=True)


if __name__ == "__main__":
    api_key = os.getenv("AGENTVERSE_API_KEY", "").strip()
    port    = int(os.getenv("AGENT_PORT", "8001"))
    mailbox = bool(api_key)

    agent = create_agentverse_agent(
        name=os.getenv("AGENT_NAME", "quorum-validator"),
        seed=os.getenv("AGENT_SEED", "quorum_agentverse_seed_v1"),
        port=port,
        mailbox=mailbox,
    )

    print(f"[quorum] Agent address : {agent.address}", flush=True)
    print(f"[quorum] Local port    : {port}", flush=True)
    print(f"[quorum] Mailbox       : {'enabled — auto-registering on Agentverse…' if mailbox else 'disabled (local only)'}", flush=True)
    print("[quorum] Starting…\n", flush=True)

    if mailbox and api_key:
        t = threading.Thread(
            target=_register_on_agentverse,
            args=(port, api_key),
            daemon=True,
        )
        t.start()

    agent.run()
