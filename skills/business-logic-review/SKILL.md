---
name: business-logic-review
description: >
  Review business-logic and invariant bugs: broken protocol invariants, incorrect fee
  math, unhandled edge cases (zero/max values, empty arrays), state-machine errors,
  EOA-only assumptions, and dangerous composability between individually-safe contracts.
  The hardest, highest-value class - use on every audit after the mechanical checks.
---

# Business Logic & Invariant Review

Mechanical detectors miss these; they require understanding what the protocol is
*supposed* to guarantee.

## Checklist
1. **State the invariants** the protocol must always hold (e.g. "sum of user balances ==
   totalSupply", "collateral value ≥ debt value", "shares·price == assets"). Then look
   for any path that can break each one.
2. **Fee math:** over/under-charging, rounding that leaks value, fees applied twice or
   skipped, fee-on-fee.
3. **Edge cases:** zero amount, `type(uint256).max`, empty arrays, single-element lists,
   self-transfer (`from == to`), first/last user, paused state, re-entrant ordering.
4. **State machine:** can steps be skipped, repeated, or run out of order (e.g. claim
   before vest, withdraw before deposit settles, double-finalize)?
5. **EOA assumptions:** `require(msg.sender == tx.origin)` or `isContract()` gates are
   bypassable (constructor code has no code size; account abstraction). Don't rely on them
   for security.
6. **Composability:** two safe contracts combined unsafely — e.g. a vault whose share
   price feeds another protocol's collateral valuation (read-only reentrancy, oracle).
7. **Economic incentives:** is there a profitable sequence of legitimate calls that
   extracts value (no "bug" per line, but a broken invariant overall)?

## Confirm vs downgrade
- CONFIRMED: a concrete call sequence that breaks a stated invariant for profit.
- Downgrade: invariant provably preserved across all paths; EOA gate not load-bearing.

## Remediation
- Encode invariants as `require`/`assert` checks and invariant tests (fuzzing).
- Handle zero/max/empty explicitly; make state transitions one-way where intended.
- Never rely on EOA checks for security guarantees.
