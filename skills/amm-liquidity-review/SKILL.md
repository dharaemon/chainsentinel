---
name: amm-liquidity-review
description: >
  Review AMM/DEX and vault-share mechanics: first-depositor/share-inflation attacks,
  donation attacks on balance-based accounting, pool imbalance, K/invariant violations,
  LP-token mispricing, JIT liquidity. Use for ERC-4626 vaults, AMMs, and LP integrations.
---

# AMM / Liquidity / Vault-Share Review

## Checklist
1. **First-depositor / share inflation (ERC-4626 & forks):**
   - Does the first deposit mint shares 1:1 with no protection? Attacker deposits 1 wei,
     donates a large amount directly to the vault, inflating share price so the next
     depositor's shares round to 0 and their funds are stolen.
   - Look for virtual shares / decimals offset / dead-shares minted on init / a minimum
     initial liquidity burn. Absence = high risk.
2. **Donation attack:** any accounting that uses `balanceOf(address(this))` instead of an
   internal tracked balance can be skewed by direct token transfers. Flag it.
3. **Invariant (x*y=k) checks:** custom AMMs must enforce the invariant after swaps;
   verify fee handling doesn't let k decrease.
4. **LP valuation:** pricing LP tokens by `reserves`/`totalSupply` spot is flash-loan
   manipulable — see oracle-price-review. Use fair-reserves formula.
5. **Slippage / min-out:** swaps and liquidity ops must take user `minAmountOut`/deadline.
6. **JIT liquidity:** fee logic that lets someone add liquidity right before a big swap
   and remove right after.

## Confirm vs downgrade
- CONFIRMED: vault with 1:1 first mint + balance-based assets and no inflation guard.
- Downgrade: virtual shares/offset present (OZ ERC4626 defaults), internal balance
  accounting, enforced invariants + slippage.

## Remediation
- Virtual shares/decimals offset (OZ 4626) or mint dead shares on initialization.
- Track balances internally; never trust raw `balanceOf` for accounting.
- Enforce invariants post-swap; require slippage bounds + deadlines; fair LP pricing.
