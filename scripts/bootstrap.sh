#!/usr/bin/env bash
# ChainSentinel bootstrap - idempotent setup + smoke test.
# Works on macOS/Linux. Safe to re-run. Does NOT send any transaction.
#
# Usage:
#   scripts/bootstrap.sh [--with-slither] [--install-skills] [--sample 0xADDR] [--chain bsc]
#
# What it does:
#   1. Locates (or clones) the repo and cd's to its root.
#   2. Creates a .venv and installs core deps (PyYAML) + pytest.
#   3. Optionally installs Slither (--with-slither) and the editable CLI.
#   4. Creates .env from .env.example if missing (never overwrites).
#   5. Runs the offline test suite.
#   6. Optionally installs the review skills into ~/.claude/skills (--install-skills).
#   7. Optionally runs a live proxy check against --sample to prove it works.
set -euo pipefail

REPO_URL="https://github.com/dharaemon/chainsentinel.git"
WITH_SLITHER=0
INSTALL_SKILLS=0
SAMPLE=""
CHAIN="bsc"

while [ $# -gt 0 ]; do
  case "$1" in
    --with-slither)   WITH_SLITHER=1 ;;
    --install-skills) INSTALL_SKILLS=1 ;;
    --sample)         SAMPLE="${2:-}"; shift ;;
    --chain)          CHAIN="${2:-bsc}"; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }

# --- 1. Locate or clone the repo ------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -f "$SCRIPT_DIR/../pyproject.toml" ] && grep -q 'name = "chainsentinel"' "$SCRIPT_DIR/../pyproject.toml" 2>/dev/null; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "./pyproject.toml" ] && grep -q 'name = "chainsentinel"' ./pyproject.toml 2>/dev/null; then
  ROOT="$(pwd)"
else
  say "Repo not found locally; cloning $REPO_URL ..."
  git clone "$REPO_URL" chainsentinel
  ROOT="$(cd chainsentinel && pwd)"
fi
cd "$ROOT"
say "Repo root: $ROOT"

# --- 2. Python + venv ------------------------------------------------------
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ and retry." >&2; exit 1
fi
PYVER="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
say "Using $PY ($PYVER)"

if [ ! -d .venv ]; then
  say "Creating virtualenv (.venv) ..."
  "$PY" -m venv .venv
fi
VPY=".venv/bin/python"
[ -x "$VPY" ] || VPY=".venv/Scripts/python.exe"   # Windows git-bash fallback

say "Installing core dependencies ..."
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet -r requirements.txt pytest

# --- 3. Optional extras ----------------------------------------------------
if [ "$WITH_SLITHER" -eq 1 ]; then
  say "Installing Slither + solc-select (optional static analysis) ..."
  "$VPY" -m pip install --quiet slither-analyzer solc-select || warn "Slither install failed; continuing without it."
fi
# Editable install gives you the `chainsentinel` command inside the venv.
"$VPY" -m pip install --quiet -e . 2>/dev/null || warn "Editable install skipped (module mode still works)."

# --- 4. .env ---------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  say "Created .env from template. Add your ETHERSCAN_API_KEY to enable source fetch."
else
  say ".env already present (left unchanged)."
fi

# --- 5. Tests --------------------------------------------------------------
say "Running offline test suite ..."
"$VPY" -m pytest -q

# --- 6. Install skills into Claude Code (optional) -------------------------
if [ "$INSTALL_SKILLS" -eq 1 ]; then
  DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
  say "Installing review skills into $DEST ..."
  mkdir -p "$DEST"
  cp -R skills/* "$DEST"/
  say "Skills installed. In Claude Code: 'audit this contract 0x...'"
fi

# --- 7. Live smoke test (optional) ----------------------------------------
if [ -n "$SAMPLE" ]; then
  say "Live proxy check: $SAMPLE on $CHAIN ..."
  "$VPY" -m chainsentinel proxy "$SAMPLE" --chain "$CHAIN" || warn "Proxy check failed (network/RPC?)."
fi

cat <<EOF

$(say "ChainSentinel is ready.")
Next:
  1. Put your free Etherscan V2 key in .env         (ETHERSCAN_API_KEY=...)
  2. Run an audit:
       .venv/bin/python -m chainsentinel audit 0xCONTRACT --chain $CHAIN --ai none --out reports
  3. Or let an AI review it:
       .venv/bin/python -m chainsentinel audit 0xCONTRACT --ai claude --print

Read-only tool: it never signs, deploys, or sends transactions.
EOF
