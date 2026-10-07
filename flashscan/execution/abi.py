"""Minimal ABI encoding for the one call the keeper makes: startArbitrage.

Dependency-free (uses our pure-Python keccak for the selector). Encodes
    startArbitrage(address asset, uint256 amount, Hop[] hops)
where Hop is the static tuple (address router, address tokenIn, address
tokenOut, uint256 minOut).
"""

from __future__ import annotations

from dataclasses import dataclass

from .keccak import selector

START_ARBITRAGE_SIG = "startArbitrage(address,uint256,(address,address,address,uint256)[])"
START_ARBITRAGE_SELECTOR = selector(START_ARBITRAGE_SIG)

# Aave V3 Pool.FLASHLOAN_PREMIUM_TOTAL() -> uint128
FLASH_PREMIUM_SELECTOR = selector("FLASHLOAN_PREMIUM_TOTAL()")


@dataclass
class Hop:
    router: str
    token_in: str
    token_out: str
    min_out: int


def _word(x: int) -> bytes:
    if x < 0:
        raise ValueError("negative uint")
    return x.to_bytes(32, "big")


def _addr_word(a: str) -> bytes:
    h = a.lower().replace("0x", "")
    if len(h) != 40:
        raise ValueError(f"bad address: {a}")
    return bytes(12) + bytes.fromhex(h)


def encode_start_arbitrage(asset: str, amount: int, hops: list[Hop]) -> bytes:
    """Return the full calldata (selector + args) for startArbitrage."""
    head = b""
    head += _addr_word(asset)
    head += _word(amount)
    head += _word(0x60)  # offset to the hops array (3 head words * 32)

    tail = _word(len(hops))
    for h in hops:
        tail += _addr_word(h.router)
        tail += _addr_word(h.token_in)
        tail += _addr_word(h.token_out)
        tail += _word(h.min_out)

    return START_ARBITRAGE_SELECTOR + head + tail


def calldata_hex(asset: str, amount: int, hops: list[Hop]) -> str:
    return "0x" + encode_start_arbitrage(asset, amount, hops).hex()
