#!/usr/bin/env bash
# ============================================================
# Quorum — project runner
# Usage:
#   ./run.sh            → start everything (Redis + API + Dashboard)
#   ./run.sh api        → API server only
#   ./run.sh dashboard  → Dashboard only
#   ./run.sh demo       → Weather demo (Fetch.ai Bureau — real pipeline)
#   ./run.sh test       → Run pytest suite
#   ./run.sh smoke      → Live smoke test (API + Dashboard must be running)
#   ./run.sh verify     → Start everything, run smoke + dashboard checks, then stop
#   ./run.sh stop       → Kill background processes
# ============================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
PID_FILE="$PROJECT_DIR/.quorum_pids"

# ── Helpers ─────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BLUE}[quorum]${RESET} $*"; }
success() { echo -e "${GREEN}[quorum]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[quorum]${RESET} $*"; }
die()     { echo -e "${RED}[quorum] ERROR:${RESET} $*" >&2; exit 1; }

require() { command -v "$1" >/dev/null 2>&1 || die "'$1' not found. Please install it."; }

# Kill every process listening on a given port
kill_port() {
  local port="$1"
  lsof -ti :"$port" 2>/dev/null | xargs kill -9 2>/dev/null || true
}

# Kill any Next.js/node process that has files open inside our dashboard dir
kill_dashboard_procs() {
  # lsof +D is macOS-compatible; suppress noise
  lsof +D "$PROJECT_DIR/dashboard" 2>/dev/null \
    | awk 'NR>1 && $1~/node/ {print $2}' \
    | sort -u \
    | xargs kill -9 2>/dev/null || true
  # Belt-and-suspenders: also kill by command pattern
  pkill -9 -f "next-server" 2>/dev/null || true
  pkill -9 -f "next dev"    2>/dev/null || true
}

activate_venv() {
  if [ ! -f "$VENV/bin/activate" ]; then
    info "Creating Python virtual environment…"
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -e "$PROJECT_DIR/[dev]" --quiet
    success "Virtual environment ready"
  else
    source "$VENV/bin/activate"
  fi
  # Ensure playwright chromium is available (needed for Browserbase CDP)
  if python -c "import playwright" 2>/dev/null; then
    python -m playwright install chromium --quiet 2>/dev/null || true
  fi
}

check_env() {
  if [ ! -f "$PROJECT_DIR/.env" ]; then
    warn ".env not found — copying .env.example. Fill in your API keys before running with real validators."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  fi
}

start_redis() {
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "quorum-redis"; then
    info "Redis already running"
    return
  fi
  require docker
  info "Starting Redis via Docker…"
  docker run -d --name quorum-redis -p 6379:6379 redis:7-alpine >/dev/null 2>&1 || \
    docker start quorum-redis >/dev/null 2>&1 || \
    warn "Could not start Redis — API will fall back to in-memory store"
  sleep 1
  success "Redis started on :6379"
}

stop_all() {
  info "Stopping background processes…"

  # 1. Kill tracked PIDs
  if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
      kill -9 "$pid" 2>/dev/null && info "Killed PID $pid" || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi

  # 2. Kill anything still holding port 8000 (uvicorn) or common Next.js ports
  kill_port 8000
  for port in 3001 3002 3003 3004 3005; do
    kill_port "$port"
  done

  # 3. Kill any dangling Next.js/node processes for this project
  kill_dashboard_procs

  # 4. Small pause so the OS reclaims the sockets
  sleep 1

  docker stop quorum-redis 2>/dev/null && info "Redis stopped" || true
  success "All stopped"
}

# ── Commands ────────────────────────────────────────────────

cmd_test() {
  activate_venv
  info "Running test suite…"
  cd "$PROJECT_DIR"
  pytest -q
  echo ""
  info "Run ${BOLD}./run.sh smoke${RESET} for live end-to-end tests (requires running API + Dashboard)"
}

cmd_smoke() {
  activate_venv
  info "Running live smoke tests…"
  chmod +x "$PROJECT_DIR/tests/smoke.sh"
  chmod +x "$PROJECT_DIR/tests/dashboard_check.sh"
  "$PROJECT_DIR/tests/smoke.sh"
  "$PROJECT_DIR/tests/dashboard_check.sh"
}

cmd_verify() {
  require docker
  require node

  info "Starting full stack for verification…"
  cmd_all &
  VERIFY_PID=$!

  info "Waiting for services to be ready (10 s)…"
  sleep 10

  info "Running smoke tests…"
  chmod +x "$PROJECT_DIR/tests/smoke.sh"
  chmod +x "$PROJECT_DIR/tests/dashboard_check.sh"

  SMOKE_EXIT=0
  "$PROJECT_DIR/tests/smoke.sh" || SMOKE_EXIT=$?
  DASH_EXIT=0
  "$PROJECT_DIR/tests/dashboard_check.sh" || DASH_EXIT=$?

  stop_all

  if [ $SMOKE_EXIT -eq 0 ] && [ $DASH_EXIT -eq 0 ]; then
    success "All verification checks passed"
    exit 0
  else
    die "Verification failed (smoke=$SMOKE_EXIT, dashboard=$DASH_EXIT)"
  fi
}

cmd_api() {
  activate_venv
  check_env
  info "Starting Quorum API on http://localhost:8000 …"
  cd "$PROJECT_DIR"
  exec uvicorn quorum.api.main:app --host 0.0.0.0 --port 8000 --reload
}

cmd_dashboard() {
  require node
  info "Starting Dashboard on http://localhost:3000 …"
  cd "$PROJECT_DIR/dashboard"
  if [ ! -d "node_modules" ]; then
    info "Installing npm dependencies…"
    npm install --silent
  fi
  exec npm run dev
}

cmd_demo() {
  activate_venv
  check_env
  info "Running weather demo (Fetch.ai Bureau)…"
  info "Watch for: Weather Agent → REJECTED → Fallback Agent → ACCEPTED"
  cd "$PROJECT_DIR"
  python -m quorum.agents.demo_workflow
}

cmd_all() {
  require docker
  require node

  echo ""
  echo -e "${BOLD}  ██████╗ ██╗   ██╗ ██████╗ ██████╗ ██╗   ██╗███╗   ███╗${RESET}"
  echo -e "${BOLD}  ██╔═══██╗██║   ██║██╔═══██╗██╔══██╗██║   ██║████╗ ████║${RESET}"
  echo -e "${BOLD}  ██║   ██║██║   ██║██║   ██║██████╔╝██║   ██║██╔████╔██║${RESET}"
  echo -e "${BOLD}  ██║▄▄ ██║██║   ██║██║   ██║██╔══██╗██║   ██║██║╚██╔╝██║${RESET}"
  echo -e "${BOLD}  ╚██████╔╝╚██████╔╝╚██████╔╝██║  ██║╚██████╔╝██║ ╚═╝ ██║${RESET}"
  echo -e "${BOLD}   ╚══▀▀═╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝${RESET}"
  echo ""
  echo -e "  Trust & Consensus Layer for Fetch.ai Multi-Agent Systems"
  echo ""

  # Clean slate — kill orphaned API and dashboard processes before starting
  kill_port 8000
  kill_dashboard_procs
  for port in 3001 3002 3003 3004 3005; do kill_port "$port"; done
  sleep 0.5

  activate_venv
  check_env
  start_redis

  rm -f "$PID_FILE"

  # Start API in background
  info "Starting API server on http://localhost:8000 …"
  cd "$PROJECT_DIR"
  uvicorn quorum.api.main:app --host 0.0.0.0 --port 8000 &
  echo $! >> "$PID_FILE"
  sleep 2

  # Start Dashboard in background
  info "Starting Dashboard on http://localhost:3000 …"
  cd "$PROJECT_DIR/dashboard"
  if [ ! -d "node_modules" ]; then
    npm install --silent
  fi
  npm run dev &
  echo $! >> "$PID_FILE"
  sleep 3

  echo ""
  success "Quorum is running!"
  echo ""
  echo -e "  ${BOLD}API${RESET}         → http://localhost:8000"
  echo -e "  ${BOLD}API Docs${RESET}    → http://localhost:8000/docs"
  echo -e "  ${BOLD}Dashboard${RESET}   → http://localhost:3000"
  echo -e "  ${BOLD}WS Stream${RESET}   → ws://localhost:8000/stream"
  echo ""
  echo -e "  Press ${BOLD}Ctrl+C${RESET} or run ${BOLD}./run.sh stop${RESET} to quit"
  echo ""

  # Wait for Ctrl+C
  trap 'stop_all; exit 0' INT TERM
  wait
}

# ── Router ───────────────────────────────────────────────────

COMMAND="${1:-all}"

case "$COMMAND" in
  all|start)  cmd_all ;;
  api)        cmd_api ;;
  dashboard)  cmd_dashboard ;;
  demo)       cmd_demo ;;
  test)       cmd_test ;;
  smoke)      cmd_smoke ;;
  verify)     cmd_verify ;;
  stop)       stop_all ;;
  *)
    echo "Usage: $0 [all|api|dashboard|demo|test|smoke|verify|stop]"
    exit 1
    ;;
esac
