"""Flashbots private-bundle client: sign + simulate + submit.

This is the "frontrun-proof" path (MEV Way 1): your transaction is sent
privately to block builders, never to the public mempool, so it cannot be
seen and sandwiched before inclusion.

Signing needs `eth-account` (pip install -r requirements-exec.txt). It is
imported lazily so the dry-run / simulate paths work with zero dependencies.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Optional

from .keccak import keccak256

DEFAULT_RELAY = "https://relay.flashbots.net"


def _require_eth_account():
    try:
        from eth_account import Account  # noqa: F401
        from eth_account.messages import encode_defunct  # noqa: F401
    except Exception as e:  # noqa: BLE001
        raise ImportError(
            "Live submission needs eth-account. Install it:\n"
            "    .venv/bin/pip install -r requirements-exec.txt"
        ) from e
    return Account, encode_defunct


class Flashbots:
    def __init__(self, private_key: str, chain_id: int = 1, relay_url: str = DEFAULT_RELAY, timeout: int = 20):
        self.Account, self.encode_defunct = _require_eth_account()
        self.key = private_key
        self.acct = self.Account.from_key(private_key)
        self.address = self.acct.address
        self.chain_id = chain_id
        self.relay_url = relay_url
        self.timeout = timeout

    # --- signing ------------------------------------------------------------
    def build_signed_tx(self, to: str, data: str, nonce: int, gas: int,
                        max_fee_wei: int, max_priority_wei: int) -> tuple[str, str]:
        """Return (raw_tx_hex, tx_hash_hex) for an EIP-1559 tx (value 0)."""
        tx = {
            "to": to,
            "value": 0,
            "data": data,
            "nonce": nonce,
            "gas": gas,
            "maxFeePerGas": max_fee_wei,
            "maxPriorityFeePerGas": max_priority_wei,
            "chainId": self.chain_id,
            "type": 2,
        }
        signed = self.Account.sign_transaction(tx, self.key)
        raw = signed.raw_transaction if hasattr(signed, "raw_transaction") else signed.rawTransaction
        h = signed.hash if hasattr(signed, "hash") else signed["hash"]
        return "0x" + raw.hex().replace("0x", ""), "0x" + h.hex().replace("0x", "")

    def _auth_header(self, body_text: str) -> str:
        digest = "0x" + keccak256(body_text.encode()).hex()
        msg = self.encode_defunct(text=digest)
        sig = self.Account.sign_message(msg, self.key).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        return f"{self.address}:{sig}"

    # --- relay RPC ----------------------------------------------------------
    def _relay_call(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        req = urllib.request.Request(
            self.relay_url, data=body.encode(),
            headers={"Content-Type": "application/json", "X-Flashbots-Signature": self._auth_header(body)},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.load(resp)
        if out.get("error"):
            raise RuntimeError(f"relay {method}: {out['error']}")
        return out.get("result")

    def simulate_bundle(self, signed_txs: list[str], block_number: int) -> dict:
        params = [{
            "txs": signed_txs,
            "blockNumber": hex(block_number),
            "stateBlockNumber": "latest",
        }]
        return self._relay_call("eth_callBundle", params)

    def send_bundle(self, signed_txs: list[str], target_block: int) -> dict:
        params = [{"txs": signed_txs, "blockNumber": hex(target_block)}]
        return self._relay_call("eth_sendBundle", params)
