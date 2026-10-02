---
name: arithmetic-review
description: >
  Review arithmetic & numeric bugs: overflow/underflow (pre-0.8 or unchecked),
  rounding/precision loss, divide-before-multiply, casting/downcast truncation,
  signed/unsigned confusion, decimal mismatches between tokens.
---

# Arithmetic & Numeric Review

## Checklist
1. **Compiler version:** `< 0.8.0` has no built-in overflow checks — require SafeMath
   everywhere. For `>= 0.8`, audit every `unchecked { }` block by hand.
2. **Rounding / precision loss:** division before multiplication truncates. Order should
   be multiply-then-divide. Small per-operation losses can be farmed at scale.
3. **Casting/truncation:** `uint256 -> uint128/uint64/...` silently drops high bits.
   Verify the value provably fits, or use SafeCast.
4. **Decimal mismatches:** mixing 18-decimal and 6/8-decimal tokens without scaling.
5. **Signed/unsigned:** `int`↔`uint` conversions; negative intermediate results wrapping.
6. **Share/asset math:** rounding direction should favor the protocol, not the user
   (round shares down on deposit, up on withdraw) — otherwise it's drainable.

## Confirm vs downgrade
- CONFIRMED: `unchecked` subtraction that can underflow with attacker input; div-before-
  mul in value/price math; truncating cast on an attacker-sized value.
- Downgrade: 0.8+ with no `unchecked`, or values provably bounded, or SafeCast used.

## Remediation
- Solidity ≥0.8 and minimize `unchecked`; SafeMath on older code.
- Multiply before divide; use mulDiv (full-precision) for ratios.
- SafeCast for narrowing; normalize decimals explicitly; round in protocol's favor.
