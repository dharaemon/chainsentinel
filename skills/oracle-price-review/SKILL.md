---
name: oracle-price-review
description: >
  Review price-oracle usage and flash-loan exposure: DEX spot-price oracles,
  flash-loan-amplified manipulation, TWAP weaknesses, stale/unbounded Chainlink data,
  single-source dependence. The #1 loss vector on BSC DeFi. Use for any contract that
  reads a price, values collateral/LP, or exposes a flash-loan callback.
---

# Oracle, Price & Flash-Loan Review

## The core attack
An attacker takes a **flash loan**, skews a price source the contract trusts within a
single transaction, interacts with the victim at the wrong price (mint/borrow/
liquidate/redeem), then repays — all atomically. Most BSC exploits are a variant of this.

## Checklist
1. **Identify every price source.** Flag these as manipulable:
   - `getReserves()`, `token0`/`token1` balances, `balanceOf(address(this))` ratios.
   - Router quotes: `getAmountsOut`, `getAmountOut`, `quote()`.
   - Any "spot" price from a single DEX pool.
2. **Flash-loan amplification:** can the price source be moved within one tx by someone
   with temporary capital? If the oracle is a DEX pool the attacker can trade against, yes.
3. **Chainlink / external feeds** — verify ALL of:
   - staleness: `updatedAt` checked against a heartbeat (`block.timestamp - updatedAt <= maxAge`).
   - round completeness: `answeredInRound >= roundId`.
   - positive price: `answer > 0`.
   - L2 sequencer uptime feed checked (on L2s).
   - min/max circuit-breaker bounds considered (depeg returns the floor, not real price).
4. **TWAP:** window long enough? low-liquidity pools make even TWAP cheap to move.
5. **Single source:** is there any sanity/deviation check against a second independent
   oracle? Single-source = high risk.
6. **Flash-loan callbacks:** `onFlashLoan` / `executeOperation` — is the initiator and
   the lender verified? Can anyone trigger the callback with crafted data?

## Confirm vs downgrade
- CONFIRMED critical: collateral/mint/redeem/liquidation priced off a DEX spot value an
  attacker can flash-loan-move.
- Downgrade: Chainlink with full freshness+completeness checks, or TWAP over deep
  liquidity with a deviation guard, or manipulation-resistant oracle (e.g. cumulative +
  bounds + multi-source).

## Remediation
- Use decentralized, manipulation-resistant oracles; never raw spot reserves.
- Add freshness, round, positivity, and deviation checks.
- Prefer TWAP over deep pools; cross-check two sources.
- Make core actions robust to same-block price moves (e.g. use oracle, not pool, price).
