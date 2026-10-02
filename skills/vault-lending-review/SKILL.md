---
name: vault-lending-review
description: >
  Review lending/staking/vault logic: reward miscalculation & double-claim, collateral
  valuation, liquidation abuse (self/under/over-liquidation), bad-debt socialization,
  interest-rate manipulation, deposit/withdraw accounting desync, emergency-withdraw
  bypass. Use for money markets, yield vaults, and staking contracts.
---

# Vault / Lending / Staking Review

## Checklist
1. **Reward accounting:** `rewardPerToken`/`accRewardPerShare` updated before every
   balance change? Can a user claim twice, or claim then withdraw then re-claim? Check
   rounding (should not let total claimed exceed funded rewards).
2. **Deposit/withdraw desync:** shares↔assets conversions consistent and rounded in the
   protocol's favor (see amm-liquidity-review for inflation).
3. **Collateral valuation:** priced via a manipulable oracle? (see oracle-price-review).
4. **Liquidation:**
   - self-liquidation for profit? under-liquidation leaving dust-but-unhealthy positions?
   - over-liquidation (seizing more than allowed)? liquidation when healthy?
   - incentive math correct and bounded?
5. **Bad debt:** if a position goes underwater, who eats it? Is socialization fair and
   not gameable by deposit-timing?
6. **Interest-rate model:** can utilization be flash-manipulated to spike/crush rates?
7. **Emergency paths:** `emergencyWithdraw` that skips accounting can desync reward/debt
   state or let someone exit without settling obligations.

## Confirm vs downgrade
- CONFIRMED: reward update-order bug enabling double claim; liquidation callable on
  healthy positions; emergency path that breaks solvency accounting.
- Downgrade: update-before-mutate invariant holds, oracle robust, liquidation health
  checks correct.

## Remediation
- Update reward/debt state before any balance mutation.
- Enforce health-factor checks on borrow/withdraw/liquidate.
- Bound liquidation incentives; settle accounting on every exit path.
