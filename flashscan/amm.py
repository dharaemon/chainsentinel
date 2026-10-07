"""Constant-product (Uniswap-V2) math and cross-DEX cycle optimisation.

All integer math mirrors the on-chain getAmountOut so quotes match reality.
"""

from __future__ import annotations

from dataclasses import dataclass


def get_amount_out(amount_in: int, reserve_in: int, reserve_out: int, fee_bps: int = 30) -> int:
    """Exact Uniswap-V2 getAmountOut (floor division, fee taken on input)."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        return 0
    amount_in_with_fee = amount_in * (10_000 - fee_bps)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 10_000 + amount_in_with_fee
    return numerator // denominator


def price_impact_bps(amount_in: int, reserve_in: int, reserve_out: int, fee_bps: int = 30) -> int:
    """Per-hop price impact in bps: (spot - exec) / spot.

    spot price = reserve_out / reserve_in; exec price = amount_out / amount_in.
    """
    out = get_amount_out(amount_in, reserve_in, reserve_out, fee_bps)
    if out == 0 or amount_in == 0:
        return 10_000
    # impact = 1 - exec/spot = 1 - (out/amount_in)/(reserve_out/reserve_in)
    #        = 1 - (out * reserve_in) / (amount_in * reserve_out)
    num = out * reserve_in
    den = amount_in * reserve_out
    if den == 0:
        return 10_000
    impact = 10_000 - (num * 10_000) // den
    return max(0, impact)


@dataclass
class CycleQuote:
    amount_in: int          # flash amount, stable smallest units
    amount_out: int         # stable returned after both hops
    gross: int              # amount_out - amount_in (stable units, can be < 0)
    impact_bps: int         # max per-hop price impact at this size


def quote_cycle(
    amount_in: int,
    res_a_stable: int, res_a_mid: int, fee_a: int,
    res_b_mid: int, res_b_stable: int, fee_b: int,
) -> CycleQuote:
    """stable --(DEX A: stable->mid)--> mid --(DEX B: mid->stable)--> stable."""
    mid = get_amount_out(amount_in, res_a_stable, res_a_mid, fee_a)
    out = get_amount_out(mid, res_b_mid, res_b_stable, fee_b)
    imp1 = price_impact_bps(amount_in, res_a_stable, res_a_mid, fee_a)
    imp2 = price_impact_bps(mid, res_b_mid, res_b_stable, fee_b)
    return CycleQuote(amount_in, out, out - amount_in, max(imp1, imp2))


def optimize_size(
    res_a_stable: int, res_a_mid: int, fee_a: int,
    res_b_mid: int, res_b_stable: int, fee_b: int,
    max_notional_units: int,
) -> CycleQuote:
    """Find the flash size maximising gross output.

    Numeric search: a geometric sweep to find the neighbourhood, then a local
    refine. Robust and dependency-free; the arb gross is unimodal in size, so
    this lands on the optimum closely enough for a scanner.
    """
    if min(res_a_stable, res_a_mid, res_b_mid, res_b_stable) <= 0:
        return CycleQuote(0, 0, 0, 10_000)

    def g(x: int) -> int:
        return quote_cycle(x, res_a_stable, res_a_mid, fee_a, res_b_mid, res_b_stable, fee_b).gross

    # Coarse geometric sweep.
    lo, hi = 1, max(2, max_notional_units)
    best_x, best_g = 1, g(1)
    x = lo
    while x <= hi:
        gx = g(x)
        if gx > best_g:
            best_g, best_x = gx, x
        x = x * 3 // 2 + 1
    # Local refine around best_x with a shrinking step.
    step = max(1, best_x // 4)
    while step > 0:
        improved = False
        for cand in (best_x - step, best_x + step):
            if cand <= 0:
                continue
            gc = g(cand)
            if gc > best_g:
                best_g, best_x, improved = gc, cand, True
        if not improved:
            step //= 2
    return quote_cycle(best_x, res_a_stable, res_a_mid, fee_a, res_b_mid, res_b_stable, fee_b)
