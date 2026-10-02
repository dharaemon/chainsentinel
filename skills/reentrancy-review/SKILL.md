---
name: reentrancy-review
description: >
  Review a contract for reentrancy: single-function, cross-function, cross-contract,
  read-only, ERC-777/hook-based, and cross-chain-callback variants. Use when auditing
  any contract that makes external calls or token transfers before finalizing state.
---

# Reentrancy Review

## What enables it
Any external interaction (`call`, `transfer`, `send`, token transfer with hooks,
callback) that happens **before** the contract finishes updating its own state.

## Checklist
1. Find every external call / value transfer. For each, check the **checks-effects-
   interactions** order: are all state writes done *before* the external call?
2. **Single-function:** balance decremented after the `.call`? classic withdraw bug.
3. **Cross-function:** does another function read/rely on state that the called-back
   function can still mutate mid-call? (e.g. `withdraw` and `transfer` sharing `balances`.)
4. **Cross-contract:** two contracts sharing state where one is re-entered via the other.
5. **Read-only reentrancy:** is a `view` function (price, share value, totalAssets)
   consumed by *other* protocols while your state is mid-update? Its return can be
   manipulated inside a callback even if your own funds are safe.
6. **Token hooks:** ERC-777 `tokensReceived`, ERC-721/1155 `onReceived`,
   `_beforeTokenTransfer`/`_afterTokenTransfer` — all hand control to attacker code.
7. **Guards:** is `nonReentrant` on every state-changing external entrypoint? A guard
   on `withdraw` but not `withdrawAll` is a gap. Note: guards don't stop read-only or
   cross-contract reentrancy.

## Confirm vs downgrade
- CONFIRMED: state update strictly after an external call to attacker-controllable
  address, no guard, reachable by anyone.
- Downgrade: `nonReentrant` present AND effects-before-interactions, or the callee is
  a fixed trusted contract with no re-entry surface.

## Remediation
- Checks-Effects-Interactions ordering.
- `ReentrancyGuard` (and `ReentrancyGuardTransient` where available).
- Pull-over-push withdrawals.
- For read-only: expose a reentrancy-aware getter or have integrators check the guard.
