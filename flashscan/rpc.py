"""Minimal JSON-RPC client + the handful of EVM calls we need.

Zero dependencies: urllib only. We hardcode the well-known 4-byte selectors so
we don't need a keccak implementation.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Optional

from .config import RPC_FALLBACKS

# Well-known function selectors (first 4 bytes of keccak(signature)).
SEL_GET_PAIR = "e6a43905"   # getPair(address,address)
SEL_GET_RESERVES = "0902f1ac"  # getReserves()
SEL_TOKEN0 = "0dfe1681"     # token0()
SEL_AGGREGATE3 = "82ad56cb"  # Multicall3.aggregate3((address,bool,bytes)[])

ZERO_ADDR = "0x0000000000000000000000000000000000000000"
# Multicall3 — same address on Ethereum and most EVM chains.
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"


class RpcError(Exception):
    pass


class Rpc:
    """A JSON-RPC client with sequential fallback across several endpoints."""

    def __init__(self, url: Optional[str] = None, timeout: int = 20,
                 fallbacks: Optional[list] = None, env_var: str = "FLASHSCAN_RPC"):
        import os
        if url:
            self.urls = [url]
        else:
            # Use ONLY this chain's own RPC env var (e.g. FLASHSCAN_RPC_BASE),
            # then its public fallbacks. We deliberately do NOT fall back to the
            # generic FLASHSCAN_RPC, which is Ethereum's — using it for an L2
            # would read the wrong chain.
            env = os.environ.get(env_var)
            self.urls = [env] if env else list(fallbacks or RPC_FALLBACKS)
        self.timeout = timeout
        self.active: Optional[str] = None

    def _call_one(self, url: str, method: str, params: list):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.load(resp)
        if "error" in body and body["error"]:
            raise RpcError(f"{method}: {body['error']}")
        return body.get("result")

    def call(self, method: str, params: list):
        """Try each endpoint until one answers; remember the one that worked."""
        order = ([self.active] if self.active else []) + [u for u in self.urls if u != self.active]
        last = None
        for url in order:
            try:
                res = self._call_one(url, method, params)
                self.active = url
                return res
            except Exception as e:  # noqa: BLE001 - fall through to next endpoint
                last = e
                continue
        raise RpcError(f"all RPC endpoints failed for {method}: {last}")

    # --- high-level helpers --------------------------------------------------
    def eth_call(self, to: str, data_hex: str) -> str:
        return self.call("eth_call", [{"to": to, "data": "0x" + data_hex}, "latest"])

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def gas_price_wei(self) -> int:
        return int(self.call("eth_gasPrice", []), 16)

    def get_pair(self, factory: str, token_a: str, token_b: str) -> Optional[str]:
        data = SEL_GET_PAIR + _addr(token_a) + _addr(token_b)
        res = self.eth_call(factory, data)
        addr = "0x" + res[-40:]
        return None if addr.lower() == ZERO_ADDR else "0x" + res[-40:]

    def token0(self, pair: str) -> str:
        res = self.eth_call(pair, SEL_TOKEN0)
        return "0x" + res[-40:]

    def get_reserves(self, pair: str) -> tuple[int, int]:
        res = self.eth_call(pair, SEL_GET_RESERVES)
        h = res[2:] if res.startswith("0x") else res
        reserve0 = int(h[0:64], 16)
        reserve1 = int(h[64:128], 16)
        return reserve0, reserve1

    # --- Multicall3 batching (one RPC call for many reads) ------------------
    def aggregate3(self, calls: list[tuple[str, str]]) -> list[tuple[bool, str]]:
        """Batch (target, data_hex) reads via Multicall3. Returns (ok, data_hex) per call."""
        data = _encode_aggregate3(calls)
        res = self.eth_call(MULTICALL3, data)
        return _decode_aggregate3(res)


def _encode_aggregate3(calls: list[tuple[str, str]]) -> str:
    """ABI-encode aggregate3((address target,bool allowFailure,bytes callData)[])."""
    elems = []
    for target, data_hex in calls:
        data = bytes.fromhex(data_hex.replace("0x", ""))
        pad = (-len(data)) % 32
        elem = (
            bytes.fromhex(_addr(target))                 # target
            + (1).to_bytes(32, "big")                    # allowFailure = true
            + (0x60).to_bytes(32, "big")                 # offset to callData within tuple
            + len(data).to_bytes(32, "big")              # callData length
            + data + bytes(pad)                          # callData padded
        )
        elems.append(elem)
    n = len(elems)
    offsets, running = b"", n * 32
    for e in elems:
        offsets += running.to_bytes(32, "big")
        running += len(e)
    body = (
        (0x20).to_bytes(32, "big")                       # offset to array
        + n.to_bytes(32, "big")                          # array length
        + offsets + b"".join(elems)
    )
    return SEL_AGGREGATE3 + body.hex()


def _decode_aggregate3(ret_hex: str) -> list[tuple[bool, str]]:
    b = bytes.fromhex(ret_hex[2:] if ret_hex.startswith("0x") else ret_hex)
    arr_off = int.from_bytes(b[0:32], "big")
    n = int.from_bytes(b[arr_off:arr_off + 32], "big")
    base = arr_off + 32
    out = []
    for i in range(n):
        elem_off = int.from_bytes(b[base + i * 32:base + i * 32 + 32], "big")
        p = base + elem_off
        success = int.from_bytes(b[p:p + 32], "big") != 0
        data_off = int.from_bytes(b[p + 32:p + 64], "big")
        dp = p + data_off
        dlen = int.from_bytes(b[dp:dp + 32], "big")
        out.append((success, "0x" + b[dp + 32:dp + 32 + dlen].hex()))
    return out


def _addr(a: str) -> str:
    """Left-pad a 20-byte address to a 32-byte ABI word (hex, no 0x)."""
    return a.lower().replace("0x", "").rjust(64, "0")


def rpc_for(chain: Optional[str], url: Optional[str] = None) -> "Rpc":
    """Build an Rpc using a chain's RPC env var + public fallbacks."""
    from .config import get_chain
    ch = get_chain(chain)
    return Rpc(url=url, fallbacks=ch.rpc_fallbacks, env_var=ch.rpc_env)
