---
name: chainsentinel-setup
description: >
  Initialise and start up the ChainSentinel repo in any agent (Claude Code or
  ChatGPT Codex). Use when the user says "set up chainsentinel", "install the
  auditor", "get the repo running", "bootstrap the pentesting tool", or is starting
  from a fresh clone / new machine. Clones if needed, builds the venv, installs deps,
  creates .env, runs the tests, optionally installs the review skills, and verifies
  with a live proxy check. Read-only: never signs, deploys, or sends transactions.
---

# ChainSentinel Setup & Startup

Goal: take a machine from nothing (or a fresh clone) to a working ChainSentinel
install, and prove it runs. One script does the work; this skill tells you how to
drive it and what to do when a step needs a human decision (API keys).

Repo: `https://github.com/dharaemon/chainsentinel`

## The one command

From anywhere (the script finds or clones the repo):

```bash
bash scripts/bootstrap.sh --install-skills --sample 0xfD36E2c2a6789Db23113685031d7F16329158384
```

If you don't have the repo yet:

```bash
git clone https://github.com/dharaemon/chainsentinel.git
cd chainsentinel
bash scripts/bootstrap.sh --install-skills
```

Flags:
- `--with-slither` — also install Slither + solc-select (deeper static analysis).
- `--install-skills` — copy the review skills into `~/.claude/skills` (Claude Code).
- `--sample 0xADDR [--chain bsc]` — run a live proxy check to confirm connectivity.

The script is idempotent and never overwrites an existing `.env`.

## What "done" looks like
1. `.venv/` exists with PyYAML (+ pytest) installed.
2. `.env` exists (created from `.env.example` if it was missing).
3. `pytest` reports all tests passing.
4. (If `--sample`) a proxy result prints for the sample address.

## Step you must handle with the user: the API key
ChainSentinel needs an **Etherscan V2 unified API key** to fetch verified source
(one free key works across BSC/ETH/Polygon/etc). Proxy detection and the prompt
bundle work *without* it, but heuristics need source.

- Tell the user to get a free key at https://etherscan.io/myapikey.
- Ask them to paste it; then set it in `.env` as `ETHERSCAN_API_KEY=...`.
- **Never** invent, commit, or print a key. `.env` is gitignored — keep it that way.
- If the user declines, continue in no-source mode and say coverage is limited.

## Per-agent notes

### Claude Code
- Run the bootstrap with `--install-skills` so the audit skills land in
  `~/.claude/skills`. After that, the user can say "audit this contract 0x…" and the
  [`smart-contract-audit`](../smart-contract-audit/SKILL.md) orchestrator takes over.
- You may run the bash blocks directly.

### ChatGPT / Codex
- Codex auto-reads the repo's `AGENTS.md`; it points here. Run the same
  `scripts/bootstrap.sh`.
- Codex has no `~/.claude/skills` system — skip `--install-skills`. Instead, when
  auditing, generate the bundle with `--ai none` and read the relevant
  `skills/*/SKILL.md` files directly as your checklist:
  ```bash
  .venv/bin/python -m chainsentinel audit 0xADDR --chain bsc --ai none --out reports
  ```
  Then open `reports/*.prompt.md` plus the skill files for the flagged categories.

## Verify, then hand off
After setup, run one real check and show the user the output:

```bash
.venv/bin/python -m chainsentinel proxy 0xADDR --chain bsc
```

Then point them at the audit command and the [audit orchestrator
skill](../smart-contract-audit/SKILL.md). If anything failed (no python3, no network,
flaky public RPC), report the exact failing step and the fix — don't claim success.

## Guardrails
- Read-only. No keys beyond the explorer API key, which the user supplies and which
  never leaves `.env`.
- Don't push, delete, or reconfigure the GitHub repo as part of "setup" unless the
  user explicitly asks.
