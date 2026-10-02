---
name: external-call-review
description: >
  Review low-level external interactions: unchecked call/delegatecall/staticcall return
  values, arbitrary/attacker-controlled call targets, return-data bombing, callback gas
  griefing, and missing contract-existence checks. Use whenever the contract uses .call,
  .delegatecall, or forwards calls.
---

# External Call / Interaction Review

## Checklist
1. **Unchecked returns:** `(bool ok, ) = target.call(...)` where `ok` is ignored — the
   call can silently fail. Every low-level call's success must be checked.
2. **Arbitrary call target/data:** does a function let the caller specify `target` and
   `calldata` for a `call`/`delegatecall`? `delegatecall` to attacker code = full
   takeover (runs in this contract's storage context). `call` can impersonate the
   contract to third parties (e.g. drain approvals granted to it).
3. **Existence check:** a `call` to an address with no code returns `success = true`.
   If the contract relies on the callee doing something, verify `code.length > 0`.
4. **Return-data bomb:** a malicious callee can return huge data to blow up gas on copy;
   use assembly with bounded returndata where relevant.
5. **Callback gas griefing:** forwarding a fixed/large gas amount to untrusted callbacks.
6. **Trust boundary:** is the called contract fixed/trusted, or user-supplied?

## Confirm vs downgrade
- CONFIRMED: user-controlled `delegatecall` target; unchecked critical `call`; approval-
  draining arbitrary `call`.
- Downgrade: fixed trusted targets, checked returns, existence checks present.

## Remediation
- Check every low-level return; prefer typed interface calls / OZ `Address.functionCall`.
- Never `delegatecall` user-supplied targets; allowlist call targets.
- Verify callee code exists; bound forwarded gas and returndata.
