"""Offline tests: keccak correctness + startArbitrage calldata encoding."""

from flashscan.execution.abi import Hop, START_ARBITRAGE_SELECTOR, encode_start_arbitrage
from flashscan.execution.keccak import keccak256, selector


def test_keccak_empty_vector():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_keccak_known_selector():
    # The canonical ERC20 transfer selector is 0xa9059cbb.
    assert selector("transfer(address,uint256)").hex() == "a9059cbb"
    # And balanceOf(address) is 0x70a08231.
    assert selector("balanceOf(address)").hex() == "70a08231"


def test_startarbitrage_selector_is_4_bytes():
    assert len(START_ARBITRAGE_SELECTOR) == 4


def test_encode_layout():
    asset = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
    weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    uni = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    sushi = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
    hops = [
        Hop(uni, asset, weth, 123),
        Hop(sushi, weth, asset, 456),
    ]
    data = encode_start_arbitrage(asset, 1_000_000, hops)

    # 4 (selector) + 3 head words + (1 length + 2 hops * 4 words) = 4 + 96 + 288
    assert len(data) == 4 + 3 * 32 + (1 + 2 * 4) * 32
    assert data[:4] == START_ARBITRAGE_SELECTOR

    body = data[4:]
    # head[0] = asset (last 20 bytes)
    assert body[12:32].hex() == asset.lower()[2:]
    # head[1] = amount
    assert int.from_bytes(body[32:64], "big") == 1_000_000
    # head[2] = offset 0x60
    assert int.from_bytes(body[64:96], "big") == 0x60
    # array length = 2
    assert int.from_bytes(body[96:128], "big") == 2
    # first hop router
    assert body[128 + 12:128 + 32].hex() == uni.lower()[2:]
    # first hop minOut (4th word of hop 0)
    assert int.from_bytes(body[128 + 96:128 + 128], "big") == 123
