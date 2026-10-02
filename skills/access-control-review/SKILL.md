---
name: access-control-review
description: >
  Review authorization and initialization: missing/incorrect modifiers, public
  initializers, re-initialization, front-runnable init, tx.origin auth, broken RBAC,
  unprotected selfdestruct/withdraw/delegatecall, and privileged-function exposure.
---

# Access Control & Initialization Review

## Checklist
1. **Enumerate privileged functions** — anything that moves funds, changes config,
   mints, pauses, upgrades, sets fees, or calls `selfdestruct`/`delegatecall`. For each,
   confirm a correct modifier (`onlyOwner`, `onlyRole`, `require(msg.sender == ...)`).
2. **Missing modifier:** a state-changing admin function with no guard = critical.
3. **`tx.origin` auth:** any `require(tx.origin == ...)` is phishable — flag it.
4. **Initializers (upgradeable contracts):**
   - `initialize()` must be protected by `initializer`/`reinitializer` and not callable twice.
   - Can it be **front-run** right after deployment? (attacker calls `initialize` first → becomes owner)
   - Is the implementation's initializer disabled (`_disableInitializers()` in constructor)?
5. **Role management:** who is `DEFAULT_ADMIN_ROLE`? Can roles be granted to arbitrary
   addresses? Is `renounceRole`/`revokeRole` correct?
6. **Ownership:** is it an EOA, multisig, timelock? Is `transferOwnership` 2-step
   (`Ownable2Step`) to avoid transferring to a wrong/zero address?
7. **Unprotected sinks:** `selfdestruct`, arbitrary `call`/`delegatecall` with
   user-supplied target, raw withdraw functions.
8. **Default visibility / `public` by accident** on functions that should be internal.

## Confirm vs downgrade
- CONFIRMED critical: unguarded fund-moving / upgrade / mint / selfdestruct function,
  or re-callable / front-runnable initializer.
- Downgrade: guarded by timelock+multisig, 2-step ownership, initializers disabled.

## Remediation
- Add/verify modifiers on every privileged path; least privilege via roles.
- Replace `tx.origin` with `msg.sender`.
- `_disableInitializers()`; `initializer` once; deploy+initialize atomically.
- `Ownable2Step`; move admin to timelock + multisig.
