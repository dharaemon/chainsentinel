"""Keeper orchestration: find a plan, simulate it, and (only when explicitly
asked and safe) submit it as a private Flashbots bundle.

Three modes:
  plan      find the best opportunity, print the route + calldata. (default)
  simulate  eth_call startArbitrage against a DEPLOYED contract; report ok/revert.
  live      build + sign + bundle-simulate + privately submit. Heavily gated.

Loss-safety is structural: the contract reverts unless the trade clears a
profit, so the worst outcome of any mode is a reverted tx costing only gas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..rpc import Rpc
from . import planner
from .abi import Hop, calldata_hex


@dataclass
class KeeperResult:
    mode: str
    plan: Optional[dict]
    calldata: Optional[str]
    messages: list
    submitted: bool = False
    simulation: Optional[dict] = None


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _get_plan(demo, rpc_url, premium_bps, gas_units, slippage_bps, chain) -> Optional[planner.ExecPlan]:
    if demo:
        return planner.find_best_demo(premium_bps, gas_units, slippage_bps)
    return planner.find_best_live(rpc_url, premium_bps, gas_units, slippage_bps, chain=chain)


def run(
    mode: str = "plan",
    demo: bool = False,
    rpc_url: Optional[str] = None,
    premium_bps: int = 5,
    gas_units: int = 300_000,
    slippage_bps: int = 50,
    arb_contract: Optional[str] = None,
    executor: Optional[str] = None,
    confirm_live: bool = False,
    chain: str = "ethereum",
) -> KeeperResult:
    msgs: list[str] = []
    plan = _get_plan(demo, rpc_url, premium_bps, gas_units, slippage_bps, chain)
    if plan is None:
        msgs.append("No cross-DEX cycle found on >=2 modelled DEXes (or RPC returned nothing).")
        return KeeperResult(mode, None, None, msgs)

    data = calldata_hex(plan.asset, plan.amount, plan.hops)

    if not plan.has_edge:
        msgs.append("Best cycle has NO edge after costs (net <= 0). Nothing to execute — "
                    "this is the normal state on mainnet. Not submitting.")

    # --- plan mode ----------------------------------------------------------
    if mode == "plan":
        return KeeperResult(mode, plan.to_dict(), data, msgs)

    arb = arb_contract or _env("ARB_CONTRACT")
    if not arb:
        msgs.append("ARB_CONTRACT not set — deploy ArbitrageExecutor.sol and set ARB_CONTRACT first.")
        return KeeperResult(mode, plan.to_dict(), data, msgs)

    from ..rpc import rpc_for
    rpc = rpc_for(chain, rpc_url)
    exec_addr = executor or _env("EXECUTOR_ADDRESS")

    # --- simulate mode (eth_call against the deployed contract) -------------
    if mode in ("simulate", "live"):
        sim = _eth_call_sim(rpc, arb, data, exec_addr)
        msgs.append(f"eth_call simulation: {'OK (would succeed)' if sim['ok'] else 'REVERT — ' + sim['error']}")
        if mode == "simulate":
            return KeeperResult(mode, plan.to_dict(), data, msgs, simulation=sim)

        # --- live mode (private Flashbots bundle) ---------------------------
        if not plan.has_edge:
            msgs.append("LIVE refused: no edge (net <= 0).")
            return KeeperResult(mode, plan.to_dict(), data, msgs, simulation=sim)
        if not sim["ok"]:
            msgs.append("LIVE refused: eth_call simulation reverted.")
            return KeeperResult(mode, plan.to_dict(), data, msgs, simulation=sim)
        if not confirm_live:
            msgs.append("LIVE refused: pass --yes-live to actually submit. (Nothing sent.)")
            return KeeperResult(mode, plan.to_dict(), data, msgs, simulation=sim)

        submitted = _submit_live(rpc, arb, data, plan, msgs, chain)
        return KeeperResult(mode, plan.to_dict(), data, msgs, submitted=submitted, simulation=sim)

    msgs.append(f"Unknown mode: {mode}")
    return KeeperResult(mode, plan.to_dict(), data, msgs)


def _eth_call_sim(rpc: Rpc, arb: str, data: str, from_addr: Optional[str]) -> dict:
    call = {"to": arb, "data": data}
    if from_addr:
        call["from"] = from_addr
    try:
        rpc.call("eth_call", [call, "latest"])
        return {"ok": True, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def _submit_live(rpc: Rpc, arb: str, data: str, plan, msgs: list, chain: str = "ethereum") -> bool:
    import flashscan.config as cfg
    pk = _env("KEEPER_PK")
    if not pk:
        msgs.append("LIVE refused: KEEPER_PK not set.")
        return False
    from .flashbots import Flashbots  # lazy (needs eth-account)
    chain_id = int(_env("CHAIN_ID", str(cfg.get_chain(chain).chain_id)))
    relay = _env("FLASHBOTS_RELAY", "https://relay.flashbots.net")
    try:
        fb = Flashbots(pk, chain_id=chain_id, relay_url=relay)
    except ImportError as e:
        msgs.append(str(e))
        return False

    # nonce + fee data
    nonce = int(rpc.call("eth_getTransactionCount", [fb.address, "pending"]), 16)
    block = rpc.call("eth_getBlockByNumber", ["latest", False])
    base_fee = int(block.get("baseFeePerGas", "0x0"), 16)
    block_number = int(block["number"], 16)
    try:
        priority = int(rpc.call("eth_maxPriorityFeePerGas", []), 16)
    except Exception:  # noqa: BLE001
        priority = 2 * 10**9
    max_fee = base_fee * 2 + priority
    gas = int(plan.meta.get("gas_units", 300_000)) if plan.meta else 350_000
    gas = 400_000

    raw, tx_hash = fb.build_signed_tx(arb, data, nonce, gas, max_fee, priority)

    target = block_number + 1
    bundle_sim = fb.simulate_bundle([raw], target)
    results = (bundle_sim or {}).get("results", [])
    reverted = any(r.get("error") or r.get("revert") for r in results)
    if reverted or not results:
        msgs.append(f"LIVE refused: Flashbots bundle simulation failed/empty: {bundle_sim}")
        return False

    sent = fb.send_bundle([raw], target)
    msgs.append(f"Bundle SUBMITTED to {relay} for block {target}. tx={tx_hash} bundleHash={(sent or {}).get('bundleHash')}")
    msgs.append("If a faster searcher wins the block, the bundle simply won't be included (0 gas). "
                "That is expected and is not a loss.")
    return True
