#!/usr/bin/env bash
# flashscan — autonomous installer + launcher.
#
#   bash scripts/install_flashscan.sh [--rpc URL] [--port 8765] [--no-serve] [--no-open]
#
# Idempotent and safe to re-run. It:
#   1. creates/reuses .venv
#   2. installs the scanner core (PyYAML + pytest) and the execution signing
#      dependency (eth-account, from requirements-exec.txt)
#   3. runs the offline test suite
#   4. launches the web dashboard and (on macOS) opens it in your browser
#
# It never sends a transaction, never asks for a key, and never touches funds.
set -euo pipefail

PORT=8765
RPC=""
SERVE=1
OPEN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --rpc) RPC="${2:-}"; shift ;;
    --port) PORT="${2:-8765}"; shift ;;
    --no-serve) SERVE=0 ;;
    --no-open) OPEN=0 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

say(){ printf '\033[1;36m==>\033[0m %s\n' "$*"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"
say "Project root: $ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "python3 not found — install Python 3.10+" >&2; exit 1; }

if [ ! -d .venv ]; then
  say "Creating virtualenv (.venv)…"
  "$PY" -m venv .venv
fi
VPY=".venv/bin/python"
[ -x "$VPY" ] || VPY=".venv/Scripts/python.exe"

say "Installing core dependencies…"
"$VPY" -m pip install --quiet --upgrade pip
[ -f requirements.txt ] && "$VPY" -m pip install --quiet -r requirements.txt pytest || "$VPY" -m pip install --quiet pytest

say "Installing execution signing dependency (eth-account)…"
if [ -f requirements-exec.txt ]; then
  "$VPY" -m pip install --quiet -r requirements-exec.txt || say "eth-account install failed — plan/simulate still work; live signing won't until it's installed."
fi

say "Running offline test suite…"
"$VPY" -m pytest flashscan/ -q

say "flashscan is ready."
cat <<EOF

  Scanner/keeper CLI:
    $VPY -m flashscan.execution.cli plan --demo         # dry-run, no network
    FLASHSCAN_RPC=<rpc> $VPY -m flashscan.execution.cli plan   # live mainnet

  Web dashboard (wallet connect + scan + execute):
    $VPY -m flashscan.server --port $PORT
EOF

if [ "$SERVE" -eq 1 ]; then
  URL="http://127.0.0.1:${PORT}/"
  say "Launching dashboard at ${URL}"
  [ -n "$RPC" ] && export FLASHSCAN_RPC="$RPC"
  if [ "$OPEN" -eq 1 ] && command -v open >/dev/null 2>&1; then ( sleep 1.5; open "$URL" ) & fi
  exec "$VPY" -m flashscan.server --port "$PORT"
fi
