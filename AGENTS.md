# AGENTS.md — ChainSentinel

Instructions for AI coding agents (ChatGPT Codex, Claude Code, etc.) working in this repo.

ChainSentinel is an **AI-assisted, read-only static auditor for public smart contracts**
(BSC/EVM). It fetches public source + chain state, resolves proxies first, runs a
taxonomy-driven heuristic scan (+ optional Slither), and prepares an evidence bundle for
an AI reviewer guided by the skills in `skills/`.

## First run — bootstrap the project

```bash
bash scripts/bootstrap.sh
```

This creates `.venv`, installs deps, creates `.env`, and runs the tests. Full procedure
and per-agent notes are in [`skills/chainsentinel-setup/SKILL.md`](skills/chainsentinel-setup/SKILL.md).

## Running an audit

```bash
.venv/bin/python -m chainsentinel audit 0xCONTRACT --chain bsc --ai none --out reports
```

Reviewing the result: read `reports/*.prompt.md` and the relevant `skills/*/SKILL.md`
checklists (one per exploit class). Start from
[`skills/smart-contract-audit/SKILL.md`](skills/smart-contract-audit/SKILL.md); it runs
[`proxy-resolution`](skills/proxy-resolution/SKILL.md) **first**, then the rest.

## Hard rules
- **Read-only.** Never sign, deploy, or send a transaction. Never add code that does.
- **Secrets stay out of git.** `.env` is gitignored. Never commit, print, or fabricate an
  API key. The only secret needed is the user's Etherscan V2 key (for source fetch).
- **Heuristic hits are leads, not verdicts** — confirm in source before reporting a bug.
- **No financial advice.** Describe technical risk only.

## Conventions
- Python 3.10+, zero-dependency core (stdlib + PyYAML). Keep new runtime deps optional.
- Tests are offline (no network): `./.venv/bin/python -m pytest -q`. Add tests for new
  analyzers and proxy patterns.
- New exploit class = a category in `data/taxonomy.yaml` + a `skills/<name>/SKILL.md`.
- New analyzer = a module in `chainsentinel/analyzers/` returning `Finding`s, wired into
  `chainsentinel/orchestrator.py`.
- New chain = a `Chain` entry in `chainsentinel/chains.py`.
