---
name: storage-review
description: >
  Review state & storage correctness: inline-assembly storage slot math, storage pointer
  bugs, uninitialized storage pointers (older Solidity), packed-variable corruption,
  mapping deletion that leaves nested data, and upgrade storage-layout safety. Use when
  the contract uses assembly, custom storage slots, or is upgradeable.
---

# State & Storage Review

## Checklist
1. **Inline assembly:** audit every `assembly { }` for `sload`/`sstore` slot computation.
   Wrong slot math reads/writes unintended state. Verify slot constants match intent
   (e.g. ERC-7201 namespaced storage, EIP-1967 slots).
2. **Uninitialized storage pointers:** in old Solidity, a local struct/array pointer
   defaulting to slot 0 can overwrite critical state. Flag on legacy compilers.
3. **Packed storage corruption:** multiple variables packed in one slot; a bad cast or
   assembly write can clobber neighbors. Check dirty-high-bit handling.
4. **Mapping deletion:** `delete myStruct` does not clear nested mappings inside it —
   stale data can persist and be reused.
5. **Upgrade layout (if upgradeable):** are new variables appended only? storage gaps
   present? no reordering/removal/type-size changes that shift slots? (ties to
   proxy-resolution).
6. **Constants vs storage:** `immutable`/`constant` used where state isn't needed
   (immutables live in code, not storage — not upgrade-safe to "change").

## Confirm vs downgrade
- CONFIRMED: assembly writing a miscomputed slot; layout change across an upgrade that
  shifts existing variables.
- Downgrade: assembly with verified slots, append-only layout + gaps, modern compiler.

## Remediation
- Prefer namespaced storage (ERC-7201) for upgradeable contracts.
- Keep storage layout append-only; add `__gap`.
- Carefully audit any assembly slot math; avoid uninitialized pointers.
