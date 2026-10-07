# flashscan/execution — flash-loan arbitrage execution layer

A **real, loss-safe, frontrun-proof** flash-loan arbitrage system that sits on
top of the flashscan scanner. It is honest about what it can and cannot do.

> **Read this first.** This is **not** an income machine, and anyone who tells
> you a flash-loan bot is "guaranteed profit" is running a scam. What this *is*:
> a correctly-built system that (1) needs **zero collateral** (flash loan),
> (2) **can never lose more than gas** (the contract reverts unless the trade
> profits), and (3) **can't be sandwiched** (private Flashbots submission). What
> it is **not**: able to *win* opportunities against professional MEV searchers.
> On Ethereum mainnet it will almost always find **no edge** or **lose the race**.
> That is the system working correctly.

## The two pieces

| Piece | File | What it does |
|---|---|---|
| Contract | [`../contracts/ArbitrageExecutor.sol`](../contracts/ArbitrageExecutor.sol) | Aave V3 flash-loan receiver. Borrows, runs whitelisted V2 swaps, repays, keeps profit. **Reverts the whole tx unless profit ≥ `minProfitBps`** — the loss-safe invariant. |
| Keeper | this package | Finds the best route (via flashscan), builds calldata, simulates, and (only when told) submits a **private Flashbots bundle**. |

## Why it's safe by construction

1. **Zero collateral** — flash loans require none; you borrow and repay in one tx.
2. **Atomic** — if any hop or the final profit check fails, the *entire*
   transaction reverts. No partial trades, no dangling debt.
3. **Loss-safe invariant** — on-chain:
   `endingBalance ≥ balanceBefore + loan + premium + minProfit`, or revert.
   You cannot end a trade poorer than you started (worst case: gas on a revert).
4. **Frontrun-proof** — live submission goes through Flashbots, never the public
   mempool, so bots can't see and sandwich your tx.
5. **Access-controlled** — only owner/executor can trigger; only whitelisted
   routers/tokens allowed; no native ETH accepted.

What none of that buys you: **winning the opportunity.** See the MEV note below.

## Install

Scanner, planner, `plan`, and `simulate` modes need **nothing** beyond the repo.
Only live signing/submission needs one dependency:

```bash
.venv/bin/pip install -r requirements-exec.txt   # eth-account
```

## Usage — three modes, safest first

```bash
# 1) PLAN (default, dry-run): find the best route + print calldata. No contract needed.
.venv/bin/python -m flashscan.execution.cli plan --demo         # synthetic
FLASHSCAN_RPC=https://your-rpc .venv/bin/python -m flashscan.execution.cli plan   # live

# 2) SIMULATE: eth_call the route against a DEPLOYED contract (ok/revert). No tx sent.
FLASHSCAN_RPC=... .venv/bin/python -m flashscan.execution.cli simulate --arb 0xYOURCONTRACT

# 3) LIVE: build + sign + bundle-simulate + privately submit. Heavily gated.
export FLASHSCAN_RPC=...  ARB_CONTRACT=0xYOURCONTRACT  KEEPER_PK=0xYOURKEY
.venv/bin/python -m flashscan.execution.cli live --yes-live
```

**Live refuses to send** unless *all* of these hold: there's a real edge
(net > 0), the `eth_call` simulation passes, the Flashbots bundle simulation
passes, and you explicitly passed `--yes-live`. Otherwise it prints why and
sends nothing.

## Deploying the contract (do this on a testnet first)

1. Compile `ArbitrageExecutor.sol` (Foundry/Remix/Hardhat).
2. Deploy with `(aaveV3Pool, executorAddress, [routers], [tokens])`.
   Mainnet Aave V3 pool: `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`.
3. Whitelist the routers (Uniswap V2 `0x7a25…`, Sushi `0xd9e1…`) and the tokens
   you'll route (they're passed in the constructor, or add later via
   `setRouter` / `setToken`).
4. Point the keeper at it via `ARB_CONTRACT`.

**The keeper wallet (`KEEPER_PK`) only needs a little ETH for gas** — no trading
capital. Never put a key with real funds into an env var on a shared machine;
use a dedicated low-value keeper key.

## Tests

```bash
# Python (offline): keccak, calldata encoding, planner math
.venv/bin/python -m pytest flashscan/ -q

# Solidity (needs Foundry + an archive RPC):
#   see ../contracts/test/ArbitrageExecutor.t.sol for setup
export MAINNET_RPC=https://your-rpc && forge test -vvv
```

## The MEV reality (don't skip this)

MEV bots affect you two ways:

- **Attacking your tx (sandwich/frontrun)** — *solved here* by private Flashbots
  submission. Your trade isn't visible until it's in a block.
- **Competing for the same opportunity** — *not solvable* for a retail bot. The
  price gap is public; the fastest, best-connected searcher (compiled code,
  colocation, direct builder deals) wins it. Your bundle just won't be included,
  and you pay nothing. That's why live mainnet runs mostly do nothing.

**Your realistic options to ever land a trade:** run this on an **L2** (Base,
Arbitrum — thinner competition), or against **newer/less-liquid pairs**. Even
then it's "sometimes," never "guaranteed."

## Scope & honesty

- V2-style DEXes, 2-hop stable→volatile→stable cycles (matches the scanner).
  Uniswap V3 / Curve / multi-hop are future extensions.
- The contract is written fresh and defensively; it has **not** been
  professionally audited. Treat it as educational. Test on a testnet, start
  tiny, and read every line before you deploy real value behind it.
- This tool describes and executes technical trades. It is **not** financial
  advice, and it makes **no** income promise.
```
