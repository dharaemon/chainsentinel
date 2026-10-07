"""Turn market state into a concrete, executable arbitrage plan.

Reuses the flashscan AMM math and reserve reader, but returns execution-ready
hops (router addresses + per-hop minOut) plus the full honest economics. Pure
function `find_best_from_reserves` is unit-testable offline.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Optional

from .. import config
from ..amm import get_amount_out, optimize_size, price_impact_bps
from .abi import Hop


@dataclass
class ExecPlan:
    asset: str                 # borrowed asset address (route start/end)
    asset_symbol: str
    amount: int                # flash amount, raw units
    hops: list[Hop]
    buy_dex: str
    sell_dex: str
    mid_symbol: str
    flash_usd: float
    gross_usd: float
    premium_usd: float
    gas_usd: float
    net_usd: float
    gross_bps: int
    impact_bps: int
    slippage_bps: int
    has_edge: bool             # net_usd > 0 at scan time (NOT a guarantee you land it)
    block: Optional[int] = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["hops"] = [h.__dict__ for h in self.hops]
        return d


def _min_out(amount: int, slippage_bps: int) -> int:
    return amount * (10_000 - slippage_bps) // 10_000


def find_best_from_reserves(
    reserves: dict,
    eth_usd: Optional[float],
    gas_price_wei: int,
    premium_bps: int = config.AAVE_PREMIUM_BPS_DEFAULT,
    gas_units: int = config.GAS_UNITS_DEFAULT,
    slippage_bps: int = 50,
    ch=None,
    amount_usd: float = 0.0,
) -> Optional[ExecPlan]:
    """Scan all cross-DEX cycles; return the best plan by net USD (or None).

    amount_usd > 0 forces a fixed flash-loan size (manual override).
    """
    ch = ch or config.get_chain(None)
    gas_usd = (gas_units * gas_price_wei / 1e18) * eth_usd if eth_usd else 0.0
    best: Optional[ExecPlan] = None
    probe_notional = 10_000  # USD, used to show honest economics for no-edge cycles

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

                # Pick the trade size: manual override, else optimal (when it
                # profits), else a $10k probe so no-edge rows show real numbers.
                if amount_usd and amount_usd > 0:
                    amount = int(amount_usd * 10**dec)
                    optimal_profitable = False  # determined from gross_raw below
                else:
                    q = optimize_size(res_a_stable, res_a_mid, a.fee_bps,
                                      res_b_mid, res_b_stable, b.fee_bps, cap)
                    optimal_profitable = q.gross > 0
                    amount = q.amount_in if (q.gross > 0 and q.amount_in > 1) else (min(cap, probe_notional * 10**dec) or 1)

                mid_amt = get_amount_out(amount, res_a_stable, res_a_mid, a.fee_bps)
                final_amt = get_amount_out(mid_amt, res_b_mid, res_b_stable, b.fee_bps)
                if mid_amt == 0 or final_amt == 0:
                    continue
                gross_raw = final_amt - amount

                flash_usd = amount / 10**dec
                gross_usd = gross_raw / 10**dec
                gross_bps = int(gross_raw * 10_000 / amount) if amount else 0
                premium_usd = flash_usd * premium_bps / 10_000
                net_usd = gross_usd - premium_usd - gas_usd

                hops = [
                    Hop(a.router, ch.tokens[stable].address, ch.tokens[mid].address,
                        _min_out(mid_amt, slippage_bps)),
                    Hop(b.router, ch.tokens[mid].address, ch.tokens[stable].address,
                        _min_out(final_amt, slippage_bps)),
                ]
                imp = max(
                    price_impact_bps(amount, res_a_stable, res_a_mid, a.fee_bps),
                    price_impact_bps(mid_amt, res_b_mid, res_b_stable, b.fee_bps),
                )
                plan = ExecPlan(
                    asset=ch.tokens[stable].address, asset_symbol=stable,
                    amount=amount, hops=hops,
                    buy_dex=a.name, sell_dex=b.name, mid_symbol=mid,
                    flash_usd=round(flash_usd, 2), gross_usd=round(gross_usd, 2),
                    premium_usd=round(premium_usd, 2), gas_usd=round(gas_usd, 2),
                    net_usd=round(net_usd, 2), gross_bps=gross_bps, impact_bps=imp,
                    slippage_bps=slippage_bps,
                    has_edge=((gross_raw > 0 if amount_usd else optimal_profitable) and net_usd > 0),
                )
                # Rank: a real edge always beats no-edge; among edges, highest
                # net; among no-edge cycles, the one CLOSEST to profitable
                # (highest gross bps) so we surface a representative liquid pool,
                # not a near-dead pool whose tiny size merely minimises the loss.
                def _key(p: ExecPlan):
                    return (1 if p.has_edge else 0, p.net_usd if p.has_edge else p.gross_bps)

                if best is None or _key(plan) > _key(best):
                    best = plan
    return best


def find_best_demo(premium_bps=config.AAVE_PREMIUM_BPS_DEFAULT,
                   gas_units=config.GAS_UNITS_DEFAULT, slippage_bps=50, amount_usd=0.0) -> Optional[ExecPlan]:
    reserves = {(p.dex, p.stable, p.mid): (p.reserve_stable, p.reserve_mid) for p in config.DEMO_PAIRS}
    return find_best_from_reserves(reserves, config.DEMO_ETH_USD, config.DEMO_GAS_PRICE_WEI,
                                   premium_bps, gas_units, slippage_bps, amount_usd=amount_usd)


def find_best_live(rpc_url: Optional[str] = None, premium_bps=config.AAVE_PREMIUM_BPS_DEFAULT,
                   gas_units=config.GAS_UNITS_DEFAULT, slippage_bps=50, chain: str = "ethereum",
                   amount_usd: float = 0.0) -> Optional[ExecPlan]:
    # Reuse the scanner's live reserve reader so we don't duplicate RPC plumbing.
    from ..rpc import rpc_for
    from .. import scanner
    ch = config.get_chain(chain)
    rpc = rpc_for(ch.name, rpc_url)
    block = rpc.block_number()
    reserves = scanner._reserves_live(rpc, ch)
    eth_usd = scanner._eth_usd_live(rpc, ch)
    try:
        gas_price_wei = rpc.gas_price_wei()
    except Exception:  # noqa: BLE001
        gas_price_wei = 10 * 10**9
    plan = find_best_from_reserves(reserves, eth_usd, gas_price_wei, premium_bps, gas_units, slippage_bps, ch=ch, amount_usd=amount_usd)
    if plan:
        plan.block = block
        plan.meta = {"rpc": rpc.active, "chain": ch.name, "chain_id": ch.chain_id, "explorer": ch.explorer,
                     "eth_usd": round(eth_usd, 2) if eth_usd else None,
                     "gas_price_gwei": round(gas_price_wei / 1e9, 2)}
    return plan
