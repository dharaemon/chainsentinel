"""Chain registry.

Explorer access uses the Etherscan V2 unified API (one API key works across all
supported chains via the `chainid` query param). Public RPC endpoints are provided
as sensible defaults; override with CHAINSENTINEL_RPC_<CHAIN> env vars or --rpc.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chain:
    key: str
    name: str
    chain_id: int
    rpc: str
    explorer_api: str   # Etherscan V2 unified endpoint
    explorer_web: str
    native_symbol: str


# Etherscan V2 unified endpoint; chainid selects the network.
_V2 = "https://api.etherscan.io/v2/api"

CHAINS: dict[str, Chain] = {
    "bsc": Chain(
        key="bsc",
        name="BNB Smart Chain",
        chain_id=56,
        rpc="https://bsc-rpc.publicnode.com",
        explorer_api=_V2,
        explorer_web="https://bscscan.com",
        native_symbol="BNB",
    ),
    "bsc-testnet": Chain(
        key="bsc-testnet",
        name="BNB Smart Chain Testnet",
        chain_id=97,
        rpc="https://data-seed-prebsc-1-s1.bnbchain.org:8545",
        explorer_api=_V2,
        explorer_web="https://testnet.bscscan.com",
        native_symbol="tBNB",
    ),
    "ethereum": Chain(
        key="ethereum",
        name="Ethereum Mainnet",
        chain_id=1,
        rpc="https://ethereum-rpc.publicnode.com",
        explorer_api=_V2,
        explorer_web="https://etherscan.io",
        native_symbol="ETH",
    ),
    "polygon": Chain(
        key="polygon",
        name="Polygon PoS",
        chain_id=137,
        rpc="https://polygon-bor-rpc.publicnode.com",
        explorer_api=_V2,
        explorer_web="https://polygonscan.com",
        native_symbol="POL",
    ),
    "arbitrum": Chain(
        key="arbitrum",
        name="Arbitrum One",
        chain_id=42161,
        rpc="https://arb1.arbitrum.io/rpc",
        explorer_api=_V2,
        explorer_web="https://arbiscan.io",
        native_symbol="ETH",
    ),
    "base": Chain(
        key="base",
        name="Base",
        chain_id=8453,
        rpc="https://mainnet.base.org",
        explorer_api=_V2,
        explorer_web="https://basescan.org",
        native_symbol="ETH",
    ),
    "optimism": Chain(
        key="optimism",
        name="OP Mainnet",
        chain_id=10,
        rpc="https://mainnet.optimism.io",
        explorer_api=_V2,
        explorer_web="https://optimistic.etherscan.io",
        native_symbol="ETH",
    ),
    "avalanche": Chain(
        key="avalanche",
        name="Avalanche C-Chain",
        chain_id=43114,
        rpc="https://api.avax.network/ext/bc/C/rpc",
        explorer_api=_V2,
        explorer_web="https://snowtrace.io",
        native_symbol="AVAX",
    ),
}

ALIASES = {
    "bnb": "bsc",
    "binance": "bsc",
    "bnbchain": "bsc",
    "eth": "ethereum",
    "mainnet": "ethereum",
    "matic": "polygon",
    "arb": "arbitrum",
    "op": "optimism",
    "avax": "avalanche",
}


def get_chain(key: str) -> Chain:
    k = key.lower().strip()
    k = ALIASES.get(k, k)
    if k not in CHAINS:
        raise KeyError(
            f"Unknown chain '{key}'. Known: {', '.join(sorted(CHAINS))} "
            f"(aliases: {', '.join(sorted(ALIASES))})"
        )
    return CHAINS[k]
