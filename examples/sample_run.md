# Example runs

> Replace the address with the contract you're reviewing. These use BSC by default.

## 1. Proxy check only (fast, no API key needed)
```bash
python3 -m chainsentinel proxy 0xYourContractAddress --chain bsc
```
Expected output tells you whether it's a proxy, the implementation, and the admin.

## 2. Full audit, build the bundle but don't call a model
```bash
python3 -m chainsentinel audit 0xYourContractAddress --chain bsc --ai none --out reports
```
Produces in `reports/`:
- `*.report.md` — human-readable report (proxy, metadata, leads table)
- `*.report.json` — machine-readable
- `*.prompt.md` — ready to paste into Claude/ChatGPT/Codex

## 3. Full audit with Claude doing the review
```bash
export ETHERSCAN_API_KEY=...        # free Etherscan V2 key, works on BSC too
python3 -m chainsentinel audit 0xYourContractAddress --ai claude --out reports --print
```

## 4. Full audit with OpenAI / ChatGPT
```bash
export ETHERSCAN_API_KEY=...
export OPENAI_API_KEY=...
python3 -m chainsentinel audit 0xYourContractAddress --ai openai --out reports
```

## 5. Different chain
```bash
python3 -m chainsentinel audit 0xYourContractAddress --chain ethereum --ai none
python3 -m chainsentinel chains      # list all supported chains
```

## 6. Deeper static analysis (optional)
Install Slither + a matching solc and re-run; findings are folded in automatically.
```bash
python3 -m pip install slither-analyzer solc-select
solc-select install 0.8.20 && solc-select use 0.8.20
python3 -m chainsentinel audit 0xYourContractAddress --ai none
```
