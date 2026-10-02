"""Proxy detection and implementation resolution.

This runs FIRST in the audit pipeline. If the target is a proxy, the real logic
lives at the implementation address, so every downstream check must be pointed
there (while storage/admin stays on the proxy).

Detection strategy (in order):
  1. EIP-1167 minimal proxy  -> parse implementation out of the bytecode.
  2. EIP-1967 slots          -> implementation / admin / beacon storage slots.
  3. EIP-1822 (UUPS)         -> PROXIABLE slot.
  4. Legacy/OZ + Gnosis Safe -> known historical slots / slot 0 masterCopy.
  5. Beacon                  -> read beacon, then beacon.implementation().
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .rpc import RpcClient, RpcError

ZERO = "0x0000000000000000000000000000000000000000"

# Standardized storage slots.
EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
EIP1967_ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
EIP1967_BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
EIP1822_PROXIABLE = "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
# Deprecated OpenZeppelin slot (zos / older upgradeable proxies).
OZ_LEGACY_IMPL = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"

# beacon.implementation() selector = keccak("implementation()")[:4]
IMPLEMENTATION_SELECTOR = "0x5c60da1b"


@dataclass
class ProxyResult:
    is_proxy: bool = False
    proxy_type: str | None = None          # e.g. "EIP-1967", "EIP-1167 (minimal)", "Beacon"
    implementation: str | None = None
    admin: str | None = None
    beacon: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_proxy": self.is_proxy,
            "proxy_type": self.proxy_type,
            "implementation": self.implementation,
            "admin": self.admin,
            "beacon": self.beacon,
            "notes": self.notes,
        }


def _slot_to_address(slot_value: str | None) -> str | None:
    """A 32-byte storage word holds a right-aligned 20-byte address."""
    if not slot_value:
        return None
    h = slot_value.lower().replace("0x", "").rjust(64, "0")
    addr = "0x" + h[-40:]
    if addr == ZERO:
        return None
    # Reject non-address-looking values (small integers packed in slot 0, e.g.
    # decimals/length). A real address has entropy across its high bytes.
    tail = h[-40:]
    if int(tail, 16) < (1 << 32):   # looks like a small integer, not an address
        return None
    return addr


def _has_code(rpc: RpcClient, address: str | None) -> bool:
    """True only if the address currently holds contract bytecode."""
    if not address:
        return False
    try:
        code = rpc.get_code(address)
    except RpcError:
        return False
    return bool(code) and code != "0x"


def _parse_eip1167(code: str) -> str | None:
    """EIP-1167 minimal proxy bytecode embeds the target address verbatim.

    Pattern: 363d3d373d3d3d363d73 <20-byte addr> 5af43d82803e903d91602b57fd5bf3
    (a push-variant also exists; we match the canonical form and the common
    optimized variants by locating the delegatecall prologue marker 363d3d37).
    """
    c = (code or "").lower().replace("0x", "")
    marker = "363d3d373d3d3d363d73"
    idx = c.find(marker)
    if idx != -1:
        start = idx + len(marker)
        addr = c[start:start + 40]
        if len(addr) == 40 and addr != "0" * 40:
            return "0x" + addr
    return None


def detect(rpc: RpcClient, address: str) -> ProxyResult:
    res = ProxyResult()

    # Pull bytecode once; empty code => EOA, nothing to audit as a contract.
    try:
        code = rpc.get_code(address)
    except RpcError as e:
        res.notes.append(f"Could not fetch bytecode: {e}")
        return res

    if not code or code == "0x":
        res.notes.append("No bytecode at address (externally owned account?).")
        return res

    # 1) EIP-1167 minimal proxy
    impl = _parse_eip1167(code)
    if impl:
        res.is_proxy = True
        res.proxy_type = "EIP-1167 (minimal proxy)"
        res.implementation = impl
        res.notes.append("Immutable minimal proxy: implementation is fixed in bytecode.")
        return res

    # 2) EIP-1967
    try:
        impl = _slot_to_address(rpc.get_storage_at(address, EIP1967_IMPL))
        admin = _slot_to_address(rpc.get_storage_at(address, EIP1967_ADMIN))
        beacon = _slot_to_address(rpc.get_storage_at(address, EIP1967_BEACON))
    except RpcError as e:
        res.notes.append(f"Slot read failed: {e}")
        impl = admin = beacon = None

    if impl:
        res.is_proxy = True
        res.proxy_type = "EIP-1967 (transparent/UUPS)"
        res.implementation = impl
        res.admin = admin
        if admin:
            res.notes.append(f"Admin slot set: {admin} (controls upgrades).")
        return res

    if beacon:
        res.is_proxy = True
        res.proxy_type = "EIP-1967 Beacon"
        res.beacon = beacon
        # Resolve beacon.implementation()
        try:
            raw = rpc.call(beacon, IMPLEMENTATION_SELECTOR)
            res.implementation = _slot_to_address(raw)
        except RpcError as e:
            res.notes.append(f"Beacon implementation() call failed: {e}")
        res.notes.append(f"Beacon proxy -> beacon {beacon}.")
        return res

    # 3) EIP-1822 UUPS
    try:
        impl = _slot_to_address(rpc.get_storage_at(address, EIP1822_PROXIABLE))
    except RpcError:
        impl = None
    if impl:
        res.is_proxy = True
        res.proxy_type = "EIP-1822 (UUPS proxiable)"
        res.implementation = impl
        return res

    # 4) Legacy OZ slot
    try:
        impl = _slot_to_address(rpc.get_storage_at(address, OZ_LEGACY_IMPL))
    except RpcError:
        impl = None
    if impl:
        res.is_proxy = True
        res.proxy_type = "OpenZeppelin legacy proxy"
        res.implementation = impl
        return res

    # 5) Gnosis Safe / masterCopy at slot 0 (weak signal: require the candidate
    #    to actually be a deployed contract, else it's just packed state).
    try:
        impl = _slot_to_address(rpc.get_storage_at(address, "0x0"))
    except RpcError:
        impl = None
    if impl and _has_code(rpc, impl):
        res.is_proxy = True
        res.proxy_type = "Possible slot-0 proxy (e.g. Gnosis Safe masterCopy)"
        res.implementation = impl
        res.notes.append("Weak signal: slot 0 holds a contract address. Verify manually.")
        return res

    # 6) implementation() getter as a last resort (some custom proxies expose it)
    try:
        raw = rpc.call(address, IMPLEMENTATION_SELECTOR)
        impl = _slot_to_address(raw)
        if impl and _has_code(rpc, impl):
            res.is_proxy = True
            res.proxy_type = "Custom proxy (implementation() getter)"
            res.implementation = impl
            res.notes.append("Resolved via implementation() view call.")
            return res
    except RpcError:
        pass

    res.notes.append("No known proxy pattern detected; treating as non-proxy.")
    return res
