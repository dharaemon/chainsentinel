"""Offline tests for the AMM math and cycle optimiser (no network)."""

from flashscan.amm import get_amount_out, optimize_size, quote_cycle
from flashscan.scanner import scan


def test_get_amount_out_matches_uniswap_formula():
    # 1000 in, reserves 1_000_000 / 1_000_000, 0.30% fee.
    out = get_amount_out(1000, 1_000_000, 1_000_000, 30)
    # amountInWithFee = 1000*9970 = 9_970_000; num = 9_970_000*1_000_000;
    # den = 1_000_000*10_000 + 9_970_000 = 10_009_970_000; out = 996.
    assert out == 996


def test_zero_and_negative_inputs_are_safe():
    assert get_amount_out(0, 10, 10) == 0
    assert get_amount_out(100, 0, 10) == 0
    assert get_amount_out(100, 10, 0) == 0


def test_equal_pools_have_no_round_trip_edge():
    # Two identical pools: a round trip must lose the double fee (gross < 0).
    q = quote_cycle(10_000, 1_000_000, 500, 30, 500, 1_000_000, 30)
    assert q.gross < 0


def test_dislocation_below_fees_has_no_gross():
    # A ~0.5% gap is smaller than the 0.6% two-hop round-trip fee: gross < 0.
    q = optimize_size(
        60_000_000 * 10**6, 30_000 * 10**18, 30,
        11_940 * 10**18, 24_000_000 * 10**6, 30,
        60_000_000 * 10**6,
    )
    assert q.gross <= 0


def test_dislocation_above_fees_creates_capturable_gross():
    # A ~2% gap (buy WETH @2,000 on A, sell @2,040 on B) clears the fees.
    q = optimize_size(
        60_000_000 * 10**6, 30_000 * 10**18, 30,      # A: 2,000 USD/WETH
        12_000 * 10**18, 24_480_000 * 10**6, 30,      # B: 2,040 USD/WETH
        60_000_000 * 10**6,
    )
    assert q.gross > 0
    assert q.amount_in > 0


def test_demo_scan_runs_and_is_wellformed():
    result = scan(demo=True)
    assert result["meta"]["mode"] == "demo"
    assert "honesty" in result["meta"]
    assert isinstance(result["rows"], list) and len(result["rows"]) >= 1
    r0 = result["rows"][0]
    for k in ("route", "flash_usd", "gross_bps", "net_usd", "verdict", "note"):
        assert k in r0
    # Rows are sorted by net descending.
    nets = [r["net_usd"] for r in result["rows"]]
    assert nets == sorted(nets, reverse=True)
