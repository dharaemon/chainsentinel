"""Minimal JSON-RPC client for read-only eth_* calls.

Uses urllib from the stdlib so the tool runs with zero third-party deps for the
on-chain parts. Only read methods are exposed; there is deliberately no way to
send a signed transaction from here.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error


class RpcError(RuntimeError):
    pass


class RpcClient:
    def __init__(self, url: str, timeout: int = 20):
        self.url = url
        self.timeout = timeout
        self._id = 0

    def _call(self, method: str, params: list) -> object:
        self._id += 1
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        ).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "ChainSentinel/0.1"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.URLError as e:  # network/DNS/timeout
            raise RpcError(f"RPC request failed: {e}") from e
        if "error" in body and body["error"]:
            raise RpcError(f"RPC error for {method}: {body['error']}")
        return body.get("result")

    # --- read-only helpers -------------------------------------------------
    def get_code(self, address: str, block: str = "latest") -> str:
        return self._call("eth_getCode", [address, block])  # type: ignore[return-value]

    def get_storage_at(self, address: str, slot: str, block: str = "latest") -> str:
        return self._call("eth_getStorageAt", [address, slot, block])  # type: ignore[return-value]

    def call(self, to: str, data: str, block: str = "latest") -> str:
        return self._call("eth_call", [{"to": to, "data": data}, block])  # type: ignore[return-value]

    def chain_id(self) -> int:
        res = self._call("eth_chainId", [])
        return int(res, 16) if isinstance(res, str) else int(res)  # type: ignore[arg-type]
