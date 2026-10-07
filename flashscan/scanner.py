"""Scan orchestration: gather reserves, optimise each cross-DEX cycle, apply
the full cost stack (Aave premium + gas + price impact), and report honestly.
"""

from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from typing import Optional

from . import config
from .amm import get_amount_out, optimize_size, price_impact_bps
from .rpc import Rpc


@dataclass
class Row:
    route: str
    flash_usd: float
    gross_bps: int
    gross_usd: float
    premium_usd: float
    gas_usd: float
    net_usd: float
    impact_bps: int
    verdict: str
    note: str


# What this tool will NOT claim. Shown on every result.
HONESTY = (
    "A positive gross spread is NOT yours to capture. Every searcher sees the "
    "same public pools in the same block; the fastest / best-connected bot "
    "wins the opportunity. On Ethereum mainnet that is almost never a "
    "non-colocated retail bot. Treat any 'NET > 0' row as 'an edge existed at "
    "scan time', not 'free money you will land'."
)


def _reserves_live(rpc: Rpc, ch=None) -> dict:
    """Return {(dex, stable, mid): (res_stable, res_mid)} for existing pairs.

    Uses Multicall3 batching (2 RPC calls total) and falls back to the slower
    per-call path if the batch read fails.
    """
    ch = ch or config.get_chain(None)
    try:
        fast = _reserves_live_fast(rpc, ch)
        if fast:
            return fast
    except Exception:  # noqa: BLE001 - fall back to sequential
        pass
    return _reserves_live_sequential(rpc, ch)


def _reserves_live_fast(rpc: Rpc, ch) -> dict:
    from .rpc import SEL_GET_PAIR, SEL_GET_RESERVES, SEL_TOKEN0, _addr, ZERO_ADDR

    combos = [(dex, stable, mid)
              for stable in ch.stables for mid in ch.mids for dex in ch.dexes]

    # Round 1: getPair for every (dex, stable, mid) in one call.
    pair_calls = [
        (dex.factory, SEL_GET_PAIR + _addr(ch.tokens[stable].address) + _addr(ch.tokens[mid].address))
        for dex, stable, mid in combos
    ]
    pair_res = rpc.aggregate3(pair_calls)
    pairs = []  # (dex, stable, mid, pair_addr)
    for (dex, stable, mid), (ok, data) in zip(combos, pair_res):
        if not ok or len(data) < 66:
            continue
        addr = "0x" + data[-40:]
        if addr.lower() != ZERO_ADDR:
            pairs.append((dex, stable, mid, addr))
    if not pairs:
        return {}

    # Round 2: token0 + getReserves for every found pair in one call.
    calls = []
    for _, _, _, pair in pairs:
        calls.append((pair, SEL_TOKEN0))
        calls.append((pair, SEL_GET_RESERVES))
    res = rpc.aggregate3(calls)

    out = {}
    for i, (dex, stable, mid, pair) in enumerate(pairs):
        ok0, t0data = res[2 * i]
        ok1, rdata = res[2 * i + 1]
        if not (ok0 and ok1):
            continue
        t0 = ("0x" + t0data[-40:]).lower()
        h = rdata[2:] if rdata.startswith("0x") else rdata
        if len(h) < 128:
            continue
        r0, r1 = int(h[0:64], 16), int(h[64:128], 16)
        res_stable, res_mid = (r0, r1) if t0 == ch.tokens[stable].address.lower() else (r1, r0)
        if res_stable > 0 and res_mid > 0:
            out[(dex.name, stable, mid)] = (res_stable, res_mid)
    return out


def _reserves_live_sequential(rpc: Rpc, ch) -> dict:
    out = {}
    for stable in ch.stables:
        s = ch.tokens[stable]
        for mid in ch.mids:
            m = ch.tokens[mid]
            for dex in ch.dexes:
                try:
                    pair = rpc.get_pair(dex.factory, s.address, m.address)
                    if not pair:
                        continue
                    t0 = rpc.token0(pair).lower()
                    r0, r1 = rpc.get_reserves(pair)
                    res_stable, res_mid = (r0, r1) if t0 == s.address.lower() else (r1, r0)
                    if res_stable > 0 and res_mid > 0:
                        out[(dex.name, stable, mid)] = (res_stable, res_mid)
                except Exception:  # noqa: BLE001 - skip unreachable/odd pairs
                    continue
    return out


def _reserves_demo() -> dict:
    out = {}
    for p in config.DEMO_PAIRS:
        out[(p.dex, p.stable, p.mid)] = (p.reserve_stable, p.reserve_mid)
    return out


def _eth_usd_live(rpc: Rpc, ch=None) -> Optional[float]:
    ch = ch or config.get_chain(None)
    try:
        weth = ch.tokens[ch.eth_symbol]
        usdc = ch.tokens[ch.usd_ref]
        pair = rpc.get_pair(ch.dexes[0].factory, weth.address, usdc.address)
        if not pair:
            return None
        t0 = rpc.token0(pair).lower()
        r0, r1 = rpc.get_reserves(pair)
        res_weth, res_usdc = (r0, r1) if t0 == weth.address.lower() else (r1, r0)
        if res_weth == 0:
            return None
        return (res_usdc / 10**usdc.decimals) / (res_weth / 10**weth.decimals)
    except Exception:  # noqa: BLE001
        return None


def scan(
    rpc_url: Optional[str] = None,
    demo: bool = False,
    premium_bps: int = config.AAVE_PREMIUM_BPS_DEFAULT,
    gas_units: int = config.GAS_UNITS_DEFAULT,
    chain: str = "ethereum",
    amount_usd: float = 0.0,
) -> dict:
    """Run a full scan. Returns a JSON-serialisable dict (meta + rows).

    amount_usd > 0 forces a fixed flash-loan size (manual override); otherwise
    each route is auto-sized to its optimal amount.
    """
    ch = config.get_chain("ethereum" if demo else chain)  # demo data is Ethereum-only
    meta: dict = {
        "mode": "demo" if demo else "live",
        "chain": ch.name,
        "chain_label": ch.label,
        "chain_id": ch.chain_id,
        "explorer": ch.explorer,
        "premium_bps": premium_bps,
        "gas_units": gas_units,
        "amount_usd": amount_usd or None,
        "honesty": HONESTY,
        "dexes": [d.name for d in ch.dexes],
    }

    if demo:
        reserves = _reserves_demo()
        eth_usd = config.DEMO_ETH_USD
        gas_price_wei = config.DEMO_GAS_PRICE_WEI
        meta["block"] = None
        meta["rpc"] = None
    else:
        from .rpc import rpc_for
        rpc = rpc_for(ch.name, rpc_url)
        try:
            meta["block"] = rpc.block_number()
        except Exception as e:  # noqa: BLE001
            return {"meta": meta, "rows": [], "error": f"RPC unreachable: {e}"}
        reserves = _reserves_live(rpc, ch)
        eth_usd = _eth_usd_live(rpc, ch)
        try:
            gas_price_wei = rpc.gas_price_wei()
        except Exception:  # noqa: BLE001
            gas_price_wei = 10 * 10**9
        meta["rpc"] = rpc.active

    meta["eth_usd"] = round(eth_usd, 2) if eth_usd else None
    meta["gas_price_gwei"] = round(gas_price_wei / 1e9, 2)

    gas_eth = gas_units * gas_price_wei / 1e18
    gas_usd = gas_eth * eth_usd if eth_usd else None

    rows: list[Row] = []
    for stable in ch.stables:
        dec = ch.tokens[stable].decimals
        for mid in ch.mids:
            present = [d for d in ch.dexes if (d.name, stable, mid) in reserves]
            if len(present) < 2:
                continue
            for a, b in itertools.permutations(present, 2):
                res_a_stable, res_a_mid = reserves[(a.name, stable, mid)]
                res_b_stable, res_b_mid = reserves[(b.name, stable, mid)]
                cap = min(res_a_stable, res_b_stable)

                # Pick the trade size:
                #  - manual override (amount_usd) if given,
                #  - else the optimal size when it profits,
                #  - else a $10k probe so no-edge rows still show real numbers.
                if amount_usd and amount_usd > 0:
                    amount = int(amount_usd * 10**dec)
                else:
                    q = optimize_size(res_a_stable, res_a_mid, a.fee_bps,
                                      res_b_mid, res_b_stable, b.fee_bps, cap)
                    amount = q.amount_in if (q.gross > 0 and q.amount_in > 1) else (min(cap, 10_000 * 10**dec) or 1)
                if amount <= 0:
                    continue

                mid_amt = get_amount_out(amount, res_a_stable, res_a_mid, a.fee_bps)
                final_amt = get_amount_out(mid_amt, res_b_mid, res_b_stable, b.fee_bps)
                if mid_amt == 0 or final_amt == 0:
                    continue
                gross_raw = final_amt - amount

                flash_usd = amount / 10**dec
                gross_usd = gross_raw / 10**dec
                gross_bps = int(gross_raw * 10_000 / amount) if amount else 0
                impact_bps = max(price_impact_bps(amount, res_a_stable, res_a_mid, a.fee_bps),
                                 price_impact_bps(mid_amt, res_b_mid, res_b_stable, b.fee_bps))
                premium_usd = flash_usd * premium_bps / 10_000
                row_gas_usd = gas_usd if gas_usd is not None else 0.0
                net_usd = gross_usd - premium_usd - row_gas_usd

                if net_usd > 0:
                    verdict = "edge at scan time"
                    note = "Gross beat costs — but you still must WIN it vs every other searcher (see honesty note)."
                elif gross_usd > premium_usd:
                    verdict = "eaten by gas"
                    note = "Spread covered the Aave premium but not gas — unprofitable to execute."
                else:
                    verdict = "no edge"
                    note = "Spread does not even cover the flash-loan premium."

                rows.append(Row(
                    route=f"{stable} →{mid} ({a.name}) →{stable} ({b.name})",
                    flash_usd=round(flash_usd, 2),
                    gross_bps=gross_bps,
                    gross_usd=round(gross_usd, 2),
                    premium_usd=round(premium_usd, 2),
                    gas_usd=round(row_gas_usd, 2),
                    net_usd=round(net_usd, 2),
                    impact_bps=impact_bps,
                    verdict=verdict,
                    note=note,
                ))

    rows.sort(key=lambda r: r.net_usd, reverse=True)
    return {"meta": meta, "rows": [asdict(r) for r in rows]}
