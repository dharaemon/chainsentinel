# flashscan — Installation Guide

A read-only flash-loan arbitrage **instrument**. It reads live DEX prices across
Ethereum, Base and Arbitrum, finds the best cross-DEX route, and shows the real
profit after every cost. Read-only and honest — no key, no deposit, no income
promise. On mainnet you'll mostly see **"no edge"**; that's the truth, not a bug.

> A printable version is in [`INSTALL.pdf`](INSTALL.pdf).

## Requirements
- `git`
- Python 3.10+
- Optional: a browser with MetaMask (to connect a wallet)
- Optional: a free RPC endpoint from [alchemy.com](https://www.alchemy.com) (for live data)

## Install in one command
```bash
curl -fsSL https://raw.githubusercontent.com/dharaemon/chainsentinel/main/scripts/get-flashscan.sh | bash
```
Prefer to read the script first? The safer two-step is identical:
```bash
git clone https://github.com/dharaemon/chainsentinel.git
cd chainsentinel && bash scripts/install_flashscan.sh --no-serve
```

## Launch
```bash
cd chainsentinel
.venv/bin/python -m flashscan.server --port 8900
```
Open **http://127.0.0.1:8900/**. For live data, add your own RPC:
```bash
FLASHSCAN_RPC="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY" .venv/bin/python -m flashscan.server --port 8900
```
Per-chain RPCs: `FLASHSCAN_RPC_BASE`, `FLASHSCAN_RPC_ARBITRUM`.

## Using it
- **Demo** = sample data, offline. **Live** = real prices (needs an RPC).
- **Chain**: Ethereum / Base / Arbitrum. L2s have thinner competition.
- **Flash amount**: leave on **Auto**. Bigger loans make trades *worse* (price impact).
- **Start monitoring**: re-scans every block, reports edge / no-edge live.
- **Execute** stays locked until a wallet, a contract, and a real passing edge are all present. You sign every trade.

## Safety
- Read-only — it never sends a transaction on its own.
- **Never type your seed phrase into any website.**
- Use a throwaway wallet; test on a testnet first.
- Not financial advice; no guaranteed profit.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "No pairs" on Live | Wrong RPC — clear the field or paste a real read RPC (Alchemy), not the Flashbots relay. |
| RPC errors / 429 | Use your own Alchemy key, not public endpoints. |
| Base/Arbitrum empty | Set `FLASHSCAN_RPC_BASE` / `FLASHSCAN_RPC_ARBITRUM`. |
| Port busy | Use another `--port`; stop a server with `Ctrl+C`. |

## CLI quick reference
```bash
.venv/bin/python -m flashscan.cli --demo              # dry-run, no network
.venv/bin/python -m flashscan.cli --chain base        # live Base scan
.venv/bin/python -m flashscan.execution.cli plan --demo   # build a route + calldata
```
