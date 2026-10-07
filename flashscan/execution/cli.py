"""Keeper CLI.

    python -m flashscan.execution.cli plan      --demo
    python -m flashscan.execution.cli plan                      # live scan
    python -m flashscan.execution.cli simulate  --arb 0xDEPLOYED
    python -m flashscan.execution.cli live      --arb 0xDEPLOYED --yes-live

Dry-run (`plan`) is the default. `live` additionally requires --yes-live AND a
profitable, simulation-passing plan, or it refuses to send anything.
"""

from __future__ import annotations

import argparse
import json

from .keeper import run


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="flashscan.execution")
    p.add_argument("mode", nargs="?", default="plan", choices=["plan", "simulate", "live"])
    p.add_argument("--demo", action="store_true", help="synthetic reserves, no network")
    p.add_argument("--chain", default="ethereum", help="ethereum | base | arbitrum")
    p.add_argument("--rpc", help="JSON-RPC URL (else per-chain env / FLASHSCAN_RPC)")
    p.add_argument("--arb", help="deployed ArbitrageExecutor address (or ARB_CONTRACT env)")
    p.add_argument("--executor", help="executor address for eth_call from-field (or EXECUTOR_ADDRESS env)")
    p.add_argument("--premium-bps", type=int, default=5)
    p.add_argument("--gas-units", type=int, default=300_000)
    p.add_argument("--slippage-bps", type=int, default=50)
    p.add_argument("--yes-live", action="store_true", help="REQUIRED to actually submit in live mode")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    res = run(
        mode=args.mode, demo=args.demo, rpc_url=args.rpc,
        premium_bps=args.premium_bps, gas_units=args.gas_units, slippage_bps=args.slippage_bps,
        arb_contract=args.arb, executor=args.executor, confirm_live=args.yes_live, chain=args.chain,
    )

    if args.json:
        print(json.dumps(res.__dict__, indent=2))
        return 0

    print(f"\n=== flashscan keeper · mode={res.mode} ===")
    if res.plan:
        pl = res.plan
        print(f"best cycle : {pl['asset_symbol']} →{pl['mid_symbol']} ({pl['buy_dex']}) "
              f"→{pl['asset_symbol']} ({pl['sell_dex']})")
        print(f"flash size : ${pl['flash_usd']:,.2f}   gross {pl['gross_bps']} bps "
              f"(${pl['gross_usd']:,.2f})")
        print(f"costs      : premium ${pl['premium_usd']:,.2f} + gas ${pl['gas_usd']:,.2f}  "
              f"| max impact {pl['impact_bps']} bps")
        print(f"NET        : ${pl['net_usd']:,.2f}   -> {'EDGE at scan time' if pl['has_edge'] else 'NO EDGE'}")
        if pl.get("block"):
            print(f"block      : {pl['block']}  ({(pl.get('meta') or {}).get('rpc','')})")
        print(f"hops       : {len(pl['hops'])}")
        for i, h in enumerate(pl["hops"]):
            print(f"   [{i}] router={h['router']} in={h['token_in']} out={h['token_out']} minOut={h['min_out']}")
    if res.calldata:
        print(f"calldata   : {res.calldata[:74]}… ({len(res.calldata)//2-1} bytes)")
    print(f"submitted  : {res.submitted}")
    for m in res.messages:
        print(f"  • {m}")
    print("\nReminder: a plan with NET>0 is an edge that EXISTED at scan time, not a trade you are")
    print("guaranteed to land. On mainnet most attempts revert or lose the race — by design.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
