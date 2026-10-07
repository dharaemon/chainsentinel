# flashscan

An **honest, read-only** cross-DEX flash-loan arbitrage **scanner + simulator**
for Ethereum mainnet, with a local web UI. Zero runtime dependencies (Python
stdlib only).

It reads live constant-product DEX reserves (Uniswap V2 + SushiSwap), finds the
best cross-DEX cycle for each pair, sizes the trade optimally, and subtracts the
**Aave flash-loan premium, gas, and price impact** to show the *real* net.

## What it does NOT do (on purpose)

- It never signs, deploys, or sends a transaction. There is no private key, no
  wallet, no execution path.
- It does **not** claim a positive spread is yours. Every searcher sees the same
  public pools in the same block; the fastest / best-connected bot wins the
  opportunity. On mainnet that is almost never a non-colocated retail bot. A
  `NET > 0` row means *"an edge existed at scan time"*, not *"free money"*.

Read that twice. It's the whole reason this exists instead of a "guaranteed
daily income" bot (which is always a scam).

## Quick start

```bash
# from the repo root (uses the project .venv)

# web UI  → open the printed URL (auto-runs a demo scan on load)
.venv/bin/python -m flashscan.server            # http://127.0.0.1:8765/

# command line
.venv/bin/python -m flashscan.cli --demo        # synthetic data, no network
.venv/bin/python -m flashscan.cli               # live mainnet (needs an RPC)
.venv/bin/python -m flashscan.cli --json        # machine-readable
```

### Demo vs live

- **Demo mode** uses synthetic reserves (clearly labelled). It needs no network
  and exists so you can see the pipeline/UI work and understand the output.
- **Live mode** reads real reserves over JSON-RPC. Free public endpoints
  rate-limit heavily — set your own for reliability:

```bash
export FLASHSCAN_RPC="https://your-eth-rpc"      # Alchemy/Infura/your node
.venv/bin/python -m flashscan.cli
```

In the web UI, pick **Live** and optionally paste an RPC URL.

## Columns

| column | meaning |
|---|---|
| route | `STABLE →MID (buyDEX) →STABLE (sellDEX)` — the 2-hop cycle |
| flash size | optimal flash-loan amount (≈ USD, stablecoin-denominated) |
| gross bps | gross spread captured at the optimal size, after DEX fees |
| gross | gross profit in USD before premium/gas |
| Aave prem | flash-loan premium (default 0.05% / 5 bps) |
| gas | estimated gas cost in USD (gas units × gas price × ETH/USD) |
| **NET** | gross − premium − gas (what's actually left) |
| max impact | the larger of the two per-hop price impacts |
| verdict | `edge at scan time` / `eaten by gas` / `no edge` |

## Scope & honest limits

- **V2-style DEXes only.** Uniswap V3 (concentrated liquidity) needs the quoter
  contract + tick math and is deliberately out of scope for now.
- **2-hop cross-DEX cycles only** (stable → volatile → stable). No multi-hop
  graph search.
- **Gas is an estimate**, and the real blocker — *winning* the opportunity
  against other searchers — is not modelled because it can't be won reliably by
  this class of tool. That's stated, not hidden.
- Optimal sizing is a numeric search (geometric sweep + local refine); the arb
  gross is unimodal in size, so it lands on the optimum closely enough.

## Tests

```bash
.venv/bin/python -m pytest flashscan/tests/ -q   # offline, no network
```

## Layout

```
flashscan/
  config.py      tokens, DEXes, defaults, demo data
  rpc.py         minimal JSON-RPC client + EVM calls (urllib only)
  amm.py         constant-product math + cycle optimiser
  scanner.py     orchestration + cost stack + honest verdicts
  cli.py         command-line scan
  server.py      local web UI + JSON API
  web/index.html the UI
  tests/         offline unit tests
```
