---
name: proxy-resolution
description: >
  First step of any contract audit. Detect whether an address is a proxy (EIP-1967
  transparent/UUPS, EIP-1822, EIP-1167 minimal, beacon, Gnosis-style slot-0, custom),
  resolve the implementation, and assess upgrade authority and upgradeability risks.
  Use before any logic review so checks target the real code.
---

# Proxy Resolution & Upgradeability Review

**Always run this first.** If the target is a proxy, its logic lives elsewhere and
every other check must point at the implementation — while storage and upgrade power
stay on the proxy.

## Detect
ChainSentinel reads these standardized storage slots via `eth_getStorageAt`:
- **EIP-1967 implementation**: `0x360894...382bbc`
- **EIP-1967 admin**: `0xb53127...5d6103`
- **EIP-1967 beacon**: `0xa3f0ad...133d50`
- **EIP-1822 (UUPS) proxiable**: `0xc5f16f...22bcf7`
- **EIP-1167 minimal proxy**: implementation is embedded in bytecode (`363d3d373d3d3d363d73<addr>5af4...`).
- **Beacon**: read beacon slot → call `implementation()` (`0x5c60da1b`) on the beacon.
- **Slot 0**: Gnosis Safe `masterCopy` and some custom proxies (weak signal).

Cross-check against the explorer's own `Proxy`/`Implementation` flag.

## Checklist
1. **Is it a proxy?** If yes, record type + implementation + admin/beacon.
2. **Did the audit fetch the implementation source**, not the proxy shell? Re-fetch if not.
3. **Who can upgrade?**
   - Transparent: the ProxyAdmin / admin slot address.
   - UUPS: the implementation's `upgradeTo*`, gated by `_authorizeUpgrade`.
   - Beacon: the beacon owner (upgrades *all* proxies pointing at it at once).
   Identify whether it's an EOA, multisig, timelock, or governance. **An EOA upgrade
   key is a critical centralization risk** even if the code is flawless.
4. **UUPS footguns:**
   - Is `_authorizeUpgrade` actually access-controlled? (A missing/empty override = anyone upgrades.)
   - Is the implementation left **uninitialized**? An attacker can `initialize()` the
     logic contract and, on UUPS, `upgradeToAndCall` → `selfdestruct`/`delegatecall`
     takeover. Confirm `_disableInitializers()` in the implementation constructor.
5. **Storage layout safety:** upgrades must preserve layout. Look for gaps
   (`uint256[50] __gap`) and appended (not reordered/inserted) variables.
6. **Function selector clash** between proxy and implementation (transparent proxies
   mitigate; custom ones may not).
7. **Metamorphic risk:** `CREATE2` + `selfdestruct` deployer can swap code at the same
   address. Check deployment pattern if source hints at it.

## Confirm vs downgrade
- CONFIRMED critical: unprotected `upgradeTo`/`_authorizeUpgrade`, or uninitialized
  UUPS implementation.
- HIGH: EOA/single-key upgrade authority.
- Downgrade if: upgrades gated by a timelock + multisig, implementation initializers
  disabled, storage gaps present.

## Remediation to recommend
- Gate upgrades behind timelock + multisig (or renounce upgradeability).
- `_disableInitializers()` in implementation constructors.
- Add storage gaps; never reorder existing variables.
- Make `_authorizeUpgrade` `onlyOwner`/`onlyRole` and tested.

## Report
State proxy type, implementation address, upgrade authority (and its type), and the
single biggest upgrade-related risk — even when the logic itself is clean.
