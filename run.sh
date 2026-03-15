#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# ResearchMind — start all services
# Usage: ./run.sh
# ─────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/researchmind-backend"
FRONTEND_DIR="$SCRIPT_DIR"

# ── colours ──────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

log()  { echo -e "${CYAN}[run]${RESET} $*"; }
ok()   { echo -e "${GREEN}[ok]${RESET}  $*"; }
warn() { echo -e "${YELLOW}[warn]${RESET} $*"; }
err()  { echo -e "${RED}[err]${RESET}  $*"; }

# ── cleanup on exit ───────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  log "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null
  ok "All services stopped."
}
trap cleanup EXIT INT TERM

# ── preflight checks ─────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       ResearchMind Launcher       ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════╝${RESET}"
echo ""

# Python
if ! command -v python3 &>/dev/null; then
  err "python3 not found. Install Python 3.11+."
  exit 1
fi

# Node
if ! command -v node &>/dev/null; then
  err "node not found. Install Node.js 18+."
  exit 1
fi

# .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
  warn "Backend .env not found."
  if [ -f "$BACKEND_DIR/.env.example" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    warn "Created .env from .env.example — fill in your API keys before running again."
    exit 1
  else
    err "No .env.example either. Cannot continue."
    exit 1
  fi
fi

# Check mandatory keys in .env
MISSING=()
for key in GROQ_API_KEY ANTHROPIC_API_KEY XAI_API_KEY; do
  # At least one LLM key must be set
  val=$(grep -E "^${key}=" "$BACKEND_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
  [ -n "$val" ] && [ "$val" != "gsk_..." ] && [ "$val" != "sk-ant-..." ] && [ "$val" != "xai-..." ] && LLM_KEY_SET=1
done
if [ -z "${LLM_KEY_SET:-}" ]; then
  warn "No LLM API key set in .env (GROQ_API_KEY / ANTHROPIC_API_KEY / XAI_API_KEY)."
fi

for key in TAVILY_API_KEY SUPABASE_URL SUPABASE_SERVICE_KEY SUPABASE_JWT_SECRET; do
  val=$(grep -E "^${key}=" "$BACKEND_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
  if [ -z "$val" ] || echo "$val" | grep -qE "^\.\.\.|your-"; then
    MISSING+=("$key")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  warn "These required keys look unset in researchmind-backend/.env:"
  for k in "${MISSING[@]}"; do echo "    - $k"; done
  echo ""
  read -r -p "Continue anyway? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

# ── check if port 8000 is already in use by ResearchMind ─────
if lsof -i :8000 -sTCP:LISTEN &>/dev/null; then
  if curl -sf http://localhost:8000/health 2>/dev/null | grep -q '"provider"'; then
    ok "ResearchMind backend already running on :8000."
  else
    warn "Port 8000 is occupied by a different process. Killing it..."
    lsof -ti :8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
fi

# ── install backend deps if needed ───────────────────────────
log "Checking backend dependencies..."
if ! python3 -c "import fastapi" &>/dev/null; then
  log "Installing Python dependencies..."
  pip install -r "$BACKEND_DIR/requirements.txt" --quiet
  ok "Backend deps installed."
else
  ok "Backend deps already installed."
fi

# ── install frontend deps if needed ──────────────────────────
log "Checking frontend dependencies..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  log "Installing Node dependencies (npm install)..."
  npm install --prefix "$FRONTEND_DIR" --silent
  ok "Frontend deps installed."
else
  ok "Frontend deps already installed."
fi

# ── start backend ─────────────────────────────────────────────
echo ""
log "Starting backend on http://localhost:8000 ..."
(
  cd "$BACKEND_DIR"
  python3 -m uvicorn main:app --reload --port 8000 2>&1 | sed "s/^/${CYAN}[backend]${RESET} /"
) &
PIDS+=($!)
BACKEND_PID=$!

# Wait for backend to be ready (up to 15s)
log "Waiting for backend to be ready..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health 2>/dev/null | grep -q '"provider"'; then
    ok "Backend is up."
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    err "Backend process died. Check logs above."
    exit 1
  fi
  sleep 1
done

# ── start frontend ────────────────────────────────────────────
log "Starting frontend on http://localhost:5173 ..."
(
  cd "$FRONTEND_DIR"
  npm run dev 2>&1 | sed "s/^/${GREEN}[frontend]${RESET} /"
) &
PIDS+=($!)

# ── ready ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}┌─────────────────────────────────────┐${RESET}"
echo -e "${BOLD}│  ResearchMind is running             │${RESET}"
echo -e "${BOLD}│                                      │${RESET}"
echo -e "${BOLD}│  Frontend  →  http://localhost:5173  │${RESET}"
echo -e "${BOLD}│  Backend   →  http://localhost:8000  │${RESET}"
echo -e "${BOLD}│  API Docs  →  http://localhost:8000/docs │${RESET}"
echo -e "${BOLD}│                                      │${RESET}"
echo -e "${BOLD}│  Press Ctrl+C to stop all services   │${RESET}"
echo -e "${BOLD}└─────────────────────────────────────┘${RESET}"
echo ""

# Keep running until Ctrl+C
wait
