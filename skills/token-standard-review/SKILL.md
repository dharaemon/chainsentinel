---
name: token-standard-review
description: >
  Review ERC-20/BEP-20 handling bugs: fee-on-transfer & rebasing token mishandling,
  unchecked transfer return values, double-entrypoint tokens, approve race / infinite
  approvals, phantom functions, reentrant (ERC-777) tokens. Use for any contract that
  moves third-party tokens.
---

# Token Standard / BEP-20 Handling Review

## Checklist
1. **Unchecked return values:** many BEP-20s return `false` instead of reverting. Raw
   `token.transfer(...)` without checking the bool (or SafeERC20) can silently fail.
   Confirm SafeERC20 (`safeTransfer`/`safeTransferFrom`) is used.
2. **Fee-on-transfer tokens:** does the contract assume `amountReceived == amountSent`?
   It should measure `balanceBefore`/`balanceAfter`. Otherwise accounting over-credits.
3. **Rebasing/deflationary tokens:** balances change out of band; internal share
   accounting must not assume fixed balances.
4. **Double-entrypoint tokens:** same token reachable via two addresses (proxy +
   underlying) can bypass denylists/sweeps (TUSD-style). Flag if the contract denylists
   by token address.
5. **approve race / infinite approval:** setting a non-zero allowance over a non-zero one;
   unbounded `approve(spender, type(uint).max)` to untrusted spenders.
6. **Phantom functions:** calling a function the token doesn't implement — fallback makes
   it "succeed". Verify the token actually implements expected methods.
7. **Reentrant tokens (ERC-777):** transfer hooks → see reentrancy-review.

## Confirm vs downgrade
- CONFIRMED: unchecked transfer of a token that can return false; balance-assuming math
  with fee-on-transfer support claimed.
- Downgrade: SafeERC20 everywhere + balance-delta measurement + no denylist-by-address.

## Remediation
- SafeERC20 for all external token ops.
- Measure actual received amount via balance delta.
- Avoid assumptions about transfer amounts, denylists, or token method existence.
