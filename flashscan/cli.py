"""Command-line scan: `python -m flashscan.cli [--demo] [--rpc URL]`."""

from __future__ import annotations

import argparse
import json
import sys

from . import config
from .scanner import scan


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="flashscan", description="Honest cross-DEX flash-loan arbitrage scanner (Ethereum mainnet).")
    p.add_argument("--demo", action="store_true", help="Use synthetic reserves (no network).")
    p.add_argument("--chain", default="ethereum", help="ethereum | base | arbitrum (default ethereum).")
    p.add_argument("--rpc", help="JSON-RPC URL (else per-chain env / FLASHSCAN_RPC / public fallbacks).")
    p.add_argument("--premium-bps", type=int, default=config.AAVE_PREMIUM_BPS_DEFAULT, help="Aave flash premium in bps (default 5).")
    p.add_argument("--gas-units", type=int, default=config.GAS_UNITS_DEFAULT, help="Gas units for the arb tx (default 300000).")
    p.add_argument("--json", action="store_true", help="Emit raw JSON instead of a table.")
    args = p.parse_args(argv)

    result = scan(rpc_url=args.rpc, demo=args.demo, premium_bps=args.premium_bps,
                  gas_units=args.gas_units, chain=args.chain)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    meta = result["meta"]
    print(f"\nflashscan — chain={meta.get('chain_label', meta.get('chain'))} mode={meta['mode']} "
          f"block={meta.get('block')} ETH/USD={meta.get('eth_usd')} "
          f"gas={meta.get('gas_price_gwei')} gwei premium={meta['premium_bps']}bps")
    if result.get("error"):
        print(f"\nERROR: {result['error']}", file=sys.stderr)
        return 1

    rows = result["rows"]
    if not rows:
        print("\nNo cross-DEX pairs found on >=2 modelled DEXes (or RPC returned nothing).")
    else:
        print(f"\n{'route':<34} {'flash$':>12} {'gross bps':>9} {'gross$':>10} "
              f"{'prem$':>8} {'gas$':>8} {'NET$':>10} {'imp bps':>7}  verdict")
        print("-" * 120)
        for r in rows:
            print(f"{r['route']:<34} {r['flash_usd']:>12,.0f} {r['gross_bps']:>9} "
                  f"{r['gross_usd']:>10,.2f} {r['premium_usd']:>8,.2f} {r['gas_usd']:>8,.2f} "
                  f"{r['net_usd']:>10,.2f} {r['impact_bps']:>7}  {r['verdict']}")

    print("\n" + "\n".join("  " + line for line in _wrap(meta["honesty"], 96)))
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
