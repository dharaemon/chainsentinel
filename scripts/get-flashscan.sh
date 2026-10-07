#!/usr/bin/env bash
# flashscan — one-command installer.
#
# Installs the whole thing from scratch: clones the repo, builds a Python
# virtualenv, installs dependencies, runs the offline tests, and prints how to
# launch the dashboard. Read-only: it never sends a transaction or asks for a key.
#
# One command (review this script first if you like — piping to a shell runs it):
#   curl -fsSL https://raw.githubusercontent.com/dharaemon/chainsentinel/main/scripts/get-flashscan.sh | bash
#
# Safer two-step equivalent:
#   git clone https://github.com/dharaemon/chainsentinel.git
#   cd chainsentinel && bash scripts/install_flashscan.sh --no-serve
set -euo pipefail

REPO_URL="https://github.com/dharaemon/chainsentinel.git"
TARGET="${FLASHSCAN_DIR:-chainsentinel}"
say(){ printf '\033[1;36m==>\033[0m %s\n' "$*"; }

command -v git     >/dev/null 2>&1 || { echo "git is required — install it and retry." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 (3.10+) is required — install it and retry." >&2; exit 1; }

if [ -d "$TARGET/.git" ]; then
  say "Repo already at ./$TARGET — updating"
  git -C "$TARGET" pull --ff-only || true
else
  say "Cloning $REPO_URL -> ./$TARGET"
  git clone --depth 1 "$REPO_URL" "$TARGET"
fi

cd "$TARGET"
say "Installing (venv + deps + tests)…"
bash scripts/install_flashscan.sh --no-serve --no-open

cat <<EOF

$(say "flashscan is installed.")
Launch the dashboard:
  cd $TARGET
  .venv/bin/python -m flashscan.server --port 8900
Then open  http://127.0.0.1:8900/

For live Ethereum/L2 data, add your own RPC (free from alchemy.com):
  FLASHSCAN_RPC="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY" \\
    .venv/bin/python -m flashscan.server --port 8900
EOF
