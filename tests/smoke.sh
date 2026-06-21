#!/usr/bin/env bash
# ============================================================
# Quorum smoke test — validates the live API end-to-end
#
# Prerequisites: API must already be running on localhost:8000
# Usage: ./tests/smoke.sh
# ============================================================

set -uo pipefail

API="${QUORUM_API_URL:-http://localhost:8000}"
PASS=0
FAIL=0

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; RESET='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; ((PASS++)); }
fail() { echo -e "${RED}  ✗${RESET}  $*"; ((FAIL++)); }
info() { echo -e "${YELLOW}[smoke]${RESET} $*"; }

# ── 1. Wait for API health ───────────────────────────────────
info "Waiting for API at $API …"
for i in $(seq 1 15); do
  if curl -sf "$API/health" -o /dev/null 2>&1; then
    ok "API is healthy (attempt $i)"
    break
  fi
  if [ "$i" -eq 15 ]; then
    fail "API did not respond within 15 seconds"
    exit 1
  fi
  sleep 1
done

# ── 2. POST three claims ─────────────────────────────────────
info "Submitting test claims …"

POST_CLAIM() {
  local label="$1"
  local payload="$2"
  local resp
  resp=$(curl -sf -X POST "$API/claims/validate" \
    -H "Content-Type: application/json" \
    -d "$payload" 2>&1) || { fail "POST /claims/validate failed for $label"; return; }
  local verdict
  verdict=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('verdict','MISSING'))" 2>/dev/null)
  if [ "$verdict" = "MISSING" ]; then
    fail "$label — no 'verdict' in response: $resp"
  else
    ok "$label — verdict=$verdict"
  fi
  echo "$resp"
}

CLAIM1=$(POST_CLAIM "weather-bad" \
  '{"agent_id":"smoke-weather","workflow_id":"wf-smoke","statement":"There is 0% chance of rain tomorrow, it will be perfectly dry.","domain":"weather"}')

CLAIM2=$(POST_CLAIM "weather-good" \
  '{"agent_id":"smoke-fallback","workflow_id":"wf-smoke","statement":"There is a 70% chance of rain tomorrow based on forecast data.","domain":"weather"}')

CLAIM3=$(POST_CLAIM "sec-edgar" \
  '{"agent_id":"smoke-finance","workflow_id":"wf-smoke","statement":"The company submitted an annual SEC filing 10-K for fiscal 2025.","domain":"finance"}')

# ── 3. GET /consensus/recent ─────────────────────────────────
info "Checking /consensus/recent …"
RECENT=$(curl -sf "$API/consensus/recent" 2>&1) || { fail "GET /consensus/recent failed"; RECENT="[]"; }
COUNT=$(echo "$RECENT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
if [ "$COUNT" -gt 0 ]; then
  ok "/consensus/recent returned $COUNT items"
else
  fail "/consensus/recent returned empty list (expected items after claim submission)"
fi

# ── 4. GET /claims/provenance (list) ────────────────────────
info "Checking /claims/provenance …"
PROV=$(curl -sf "$API/claims/provenance" 2>&1) || { fail "GET /claims/provenance failed"; PROV="[]"; }
PCOUNT=$(echo "$PROV" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
if [ "$PCOUNT" -gt 0 ]; then
  ok "/claims/provenance returned $PCOUNT records"
else
  fail "/claims/provenance returned empty list"
fi

# ── 5. GET /agents/trust ─────────────────────────────────────
info "Checking /agents/trust …"
TRUST=$(curl -sf "$API/agents/trust" 2>&1) || { fail "GET /agents/trust failed"; TRUST="[]"; }
TCOUNT=$(echo "$TRUST" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
if [ "$TCOUNT" -gt 0 ]; then
  ok "/agents/trust returned $TCOUNT agent scores"
else
  fail "/agents/trust returned empty (expected trust scores after claims)"
fi

# ── 6. WebSocket event check ─────────────────────────────────
info "Checking WebSocket stream for events …"
WS_URL="${QUORUM_WS_URL:-ws://localhost:8000/stream}"

WS_EVENTS=$(python3 - "$WS_URL" "$API" <<'PYEOF' 2>/dev/null
import asyncio, json, sys, urllib.request

WS = sys.argv[1]
API = sys.argv[2]

async def check_ws():
    try:
        import websockets
    except ImportError:
        print("SKIP"); return

    async with websockets.connect(WS) as ws:
        async def post():
            await asyncio.sleep(0.4)
            req = urllib.request.Request(
                f"{API}/claims/validate",
                data=json.dumps({"agent_id":"ws-smoke","workflow_id":"wf-ws","statement":"Smoke test claim."}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try: urllib.request.urlopen(req, timeout=5)
            except Exception: pass

        asyncio.create_task(post())
        received = []
        try:
            async with asyncio.timeout(7):
                async for msg in ws:
                    evt = json.loads(msg)
                    received.append(evt.get("event_type", ""))
                    if len(received) >= 3: break
        except asyncio.TimeoutError: pass
        print(json.dumps(received))

asyncio.run(check_ws())
PYEOF
)

if [ "$WS_EVENTS" = "SKIP" ]; then
  info "WebSocket check skipped (websockets package not installed)"
elif [ -z "$WS_EVENTS" ]; then
  fail "WebSocket check failed or timed out"
else
  if echo "$WS_EVENTS" | grep -q "consensus_reached"; then
    ok "WebSocket stream delivered 'consensus_reached' event"
  else
    fail "WebSocket stream did not deliver expected events (got: $WS_EVENTS)"
  fi
fi

# ── 7. Per-claim provenance ──────────────────────────────────
info "Checking per-claim provenance endpoint …"
CLAIM_ID=$(echo "$CLAIM2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('claim_id',''))" 2>/dev/null || echo "")
if [ -n "$CLAIM_ID" ]; then
  PROV_SINGLE=$(curl -sf "$API/claims/$CLAIM_ID/provenance" 2>&1) || { fail "GET /claims/$CLAIM_ID/provenance failed"; PROV_SINGLE=""; }
  if echo "$PROV_SINGLE" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('claim_id')" 2>/dev/null; then
    ok "/claims/$CLAIM_ID/provenance — provenance record found"
  else
    fail "/claims/$CLAIM_ID/provenance — no valid record returned"
  fi
else
  fail "Could not extract claim_id from claim submission response"
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Smoke Test Results:${RESET} ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET}"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
