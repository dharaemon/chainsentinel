# 🛡️ ChainSentinel

**AI-assisted, read-only static auditor for public smart contracts (BSC & EVM).**

Give it a deployed contract address. ChainSentinel fetches the verified source and
on-chain state, **resolves any proxy first**, runs a taxonomy-driven heuristic scan
(plus Slither if installed), then hands a structured evidence bundle to an AI auditor
(**Claude, Codex, or ChatGPT**) guided by one **skill file per exploit class**.

It is **defensive and read-only**: it only reads public chain data and produces a
report. It never holds keys, signs, deploys, or sends a transaction, and it gives no
financial advice.

```
address ──▶ [1] proxy resolution ──▶ [2] fetch verified source ──▶ [3] heuristics
         ──▶ [4] Slither (optional) ──▶ [5] evidence bundle ──▶ AI review (skills)
         ──▶ report.md / report.json / prompt.md
```

---

## Why

Most BSC/DeFi losses come from a handful of classes — flash-loan + oracle price
manipulation, access-control/proxy bugs, and rug-pull/honeypot admin powers. The
exploit taxonomy in [`data/taxonomy.yaml`](data/taxonomy.yaml) enumerates ~20 classes;
each maps to a review skill in [`skills/`](skills/). The Python tool does deterministic
evidence-gathering; the AI does the judgment, steered by those skills.

## Install

Requires Python 3.10+.

```bash
git clone <your-repo-url> chainsentinel && cd chainsentinel
python3 -m pip install -r requirements.txt     # just PyYAML
# optional, for a real CLI entrypoint:
python3 -m pip install -e .
```

Optional, for deeper static analysis:
```bash
python3 -m pip install slither-analyzer solc-select
solc-select install 0.8.20 && solc-select use 0.8.20
```

## Configure

```bash
cp .env.example .env
# edit .env:  ETHERSCAN_API_KEY=...   (free Etherscan V2 key — works on BSC, ETH, Polygon, …)
```
A key is recommended (rate limits), but `proxy` detection and bundle-building work
without one.

## Usage

```bash
# Full audit (BSC default). Build the AI bundle without calling a model:
python3 -m chainsentinel audit 0xCONTRACT --chain bsc --ai none --out reports

# Let Claude do the review:
python3 -m chainsentinel audit 0xCONTRACT --ai claude --print

# ChatGPT / Codex:
python3 -m chainsentinel audit 0xCONTRACT --ai openai
python3 -m chainsentinel audit 0xCONTRACT --ai codex

# Just resolve the proxy:
python3 -m chainsentinel proxy 0xCONTRACT --chain bsc

# List chains:
python3 -m chainsentinel chains
```

After `pip install -e .` you can use the `chainsentinel` command directly instead of
`python3 -m chainsentinel`.

### Outputs
Each audit writes three files to `--out`:
- `*.report.md` — human-readable (proxy, metadata, severity rollup, leads table, AI review)
- `*.report.json` — machine-readable (feed into CI or other tools)
- `*.prompt.md` — the full evidence bundle; paste into any assistant if you used `--ai none`

## The pipeline (what each step does)

| Step | Module | What it does |
|---|---|---|
| 1. Proxy | `proxy.py` | Reads EIP-1967/1822/1167/beacon/slot-0 patterns via `eth_getStorageAt`, resolves the implementation, flags upgrade authority. **Runs first** so every later check targets the real logic. |
| 2. Source | `explorer.py` | Fetches verified source + ABI from Etherscan V2 (handles standard-json multi-file). Warns if unverified. |
| 3. Heuristics | `analyzers/heuristics.py` | Scans source for taxonomy patterns → leads tagged with category + skill. |
| 4. Slither | `analyzers/static_slither.py` | If installed, runs Slither and folds results into findings. Gracefully skipped otherwise. |
| 5. AI review | `ai_bridge.py` + `skills/` | Builds the prompt, dispatches each lead to the matching skill, asks the model to confirm/deny with location, exploit path, impact, and fix. |

## Skills

See [`skills/README.md`](skills/README.md). Install them into Claude Code:

```bash
cp -R skills/* ~/.claude/skills/     # then: "audit this contract 0x…"
```

The orchestrator skill is [`smart-contract-audit`](skills/smart-contract-audit/SKILL.md);
it always runs [`proxy-resolution`](skills/proxy-resolution/SKILL.md) first.

## Supported chains

BSC (default), BSC testnet, Ethereum, Polygon, Arbitrum, Base, Optimism, Avalanche —
all via the one Etherscan V2 key. Add more in [`chainsentinel/chains.py`](chainsentinel/chains.py).

## Extending

- **New exploit class:** add a category to `data/taxonomy.yaml` and a `SKILL.md` under `skills/`.
- **New analyzer:** add a module under `chainsentinel/analyzers/` returning `Finding`s and
  call it from `orchestrator.py`.
- **New chain:** add a `Chain` entry in `chains.py`.

## Tests

```bash
python3 -m pytest -q        # offline unit tests (no network)
```

## Scope & ethics

- **Read-only.** No transactions, no private keys, no deploys.
- Audit contracts you own or are **authorized** to review (or public contracts for
  defensive research/education). Don't use findings to attack systems you don't have
  permission to test.
- Heuristic hits are **leads, not verdicts** — confirm manually.
- Not financial advice. Technical risk ≠ investment recommendation.

## License

MIT — see [LICENSE](LICENSE).
