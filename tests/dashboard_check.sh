#!/usr/bin/env bash
# ============================================================
# Quorum dashboard check — verifies all pages load (HTTP 200)
# and the WS stream delivers events
#
# Prerequisites: Dashboard must be running on localhost:3000
#                API must be running on localhost:8000
# Usage: ./tests/dashboard_check.sh
# ============================================================

set -uo pipefail

DASHBOARD="${QUORUM_DASHBOARD_URL:-http://localhost:3000}"
API="${QUORUM_API_URL:-http://localhost:8000}"
WS_URL="${QUORUM_WS_URL:-ws://localhost:8000/stream}"
PASS=0
FAIL=0

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; RESET='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; ((PASS++)); }
fail() { echo -e "${RED}  ✗${RESET}  $*"; ((FAIL++)); }
info() { echo -e "${YELLOW}[dash]${RESET}  $*"; }

# ── 1. Wait for dashboard ────────────────────────────────────
info "Waiting for Dashboard at $DASHBOARD …"
for i in $(seq 1 20); do
  if curl -sf "$DASHBOARD" -o /dev/null 2>&1; then
    ok "Dashboard is up (attempt $i)"
    break
  fi
  if [ "$i" -eq 20 ]; then
    fail "Dashboard did not respond within 20 seconds"
    exit 1
  fi
  sleep 1
done

# ── 2. Check all pages ───────────────────────────────────────
info "Checking dashboard pages …"

CHECK_PAGE() {
  local path="$1"
  local label="$2"
  local status
  status=$(curl -sf -o /dev/null -w "%{http_code}" "$DASHBOARD$path" 2>/dev/null || echo "000")
  if [ "$status" = "200" ]; then
    ok "$label ($DASHBOARD$path) → HTTP $status"
  else
    fail "$label ($DASHBOARD$path) → HTTP $status (expected 200)"
  fi
}

CHECK_PAGE "/"          "Home/root"
CHECK_PAGE "/consensus" "Live Consensus"
CHECK_PAGE "/trust"     "Trust Scores"
CHECK_PAGE "/quarantine" "Quarantine"
CHECK_PAGE "/provenance" "Provenance"
CHECK_PAGE "/demo"      "Demo"

# ── 3. Verify page content contains expected markers ────────
info "Verifying page content …"

CHECK_CONTENT() {
  local path="$1"
  local label="$2"
  local marker="$3"
  local body
  body=$(curl -sf "$DASHBOARD$path" 2>/dev/null || echo "")
  if echo "$body" | grep -qi "$marker"; then
    ok "$label contains expected content ('$marker')"
  else
    fail "$label missing expected content ('$marker') at $DASHBOARD$path"
  fi
}

CHECK_CONTENT "/consensus" "Consensus page" "consensus"
CHECK_CONTENT "/trust"     "Trust page"     "trust"
CHECK_CONTENT "/demo"      "Demo page"      "demo"

# ── 4. WebSocket delivers events ────────────────────────────
info "Checking WebSocket delivers events …"

python3 - "$WS_URL" "$API" <<'PYEOF'
import asyncio, json, sys, urllib.request

WS = sys.argv[1]
API = sys.argv[2]

async def check():
    try:
        import websockets
    except ImportError:
        print("\033[1;33m[dash]\033[0m  WebSocket check skipped (websockets not installed)")
        sys.exit(0)

    received = []
    try:
        async with websockets.connect(WS) as ws:
            async def post():
                await asyncio.sleep(0.5)
                req = urllib.request.Request(
                    f"{API}/claims/validate",
                    data=json.dumps({"agent_id":"dash-check","workflow_id":"wf-dash","statement":"Dashboard smoke check claim."}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try: urllib.request.urlopen(req, timeout=5)
                except Exception: pass

            asyncio.create_task(post())
            try:
                async with asyncio.timeout(8):
                    async for msg in ws:
                        evt = json.loads(msg)
                        received.append(evt.get("event_type", ""))
                        if len(received) >= 2: break
            except asyncio.TimeoutError:
                pass
    except Exception as e:
        print(f"\033[0;31m  ✗\033[0m  WebSocket connection failed: {e}")
        sys.exit(1)

    if "consensus_reached" in received:
        print(f"\033[0;32m  ✔\033[0m  WebSocket delivered events: {received}")
    else:
        print(f"\033[0;31m  ✗\033[0m  WebSocket events missing 'consensus_reached' (got {received})")
        sys.exit(1)

asyncio.run(check())
PYEOF

WS_EXIT=$?
if [ $WS_EXIT -eq 0 ]; then
  ((PASS++))
else
  ((FAIL++))
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Dashboard Check Results:${RESET} ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET}"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
