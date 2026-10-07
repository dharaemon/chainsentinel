"""Chain-aware configuration: tokens, V2-style DEXes, Aave pools, RPCs.

Only constant-product ("V2-style") DEXes are modelled — their on-chain reserves
give an exact, dependency-free quote. Uniswap-V3 concentrated liquidity needs
the quoter + tick math and is out of scope.

Supported chains: Ethereum, Base, Arbitrum — all of which have Aave V3 (so the
flash-loan executor works on each). The Ethereum module-level aliases
(TOKENS/STABLES/MIDS/DEXES/AAVE_V3_POOL) are kept for backward compatibility.

L2 note: the Base/Arbitrum DEX factory addresses are the well-documented V2
deployments, but could not be live-verified from the build sandbox. The scanner
SKIPS any pair that doesn't exist, so a wrong address simply shows no pairs —
confirm which DEXes populate with one live scan on the chain.
"""

from __future__ import annotations

from dataclasses import dataclass


# --- Primitives --------------------------------------------------------------
@dataclass(frozen=True)
class Token:
    symbol: str
    address: str
    decimals: int


@dataclass(frozen=True)
class Dex:
    name: str
    factory: str
    router: str   # V2 router (swapExactTokensForTokens) — used by the executor
    fee_bps: int = 30


@dataclass(frozen=True)
class Chain:
    name: str            # key, e.g. "ethereum"
    label: str           # display name
    chain_id: int
    tokens: dict
    stables: list
    mids: list
    dexes: list
    aave_pool: str
    explorer: str        # base URL, e.g. https://etherscan.io
    rpc_env: str         # env var holding this chain's RPC URL
    rpc_fallbacks: list
    eth_symbol: str = "WETH"   # wrapped-native symbol, used to price gas
    usd_ref: str = "USDC"      # stable used as the $1 reference


# --- Economics defaults ------------------------------------------------------
AAVE_PREMIUM_BPS_DEFAULT = 5     # Aave V3 flash-loan premium is 0.05% on all chains
GAS_UNITS_DEFAULT = 300_000


# --- Chains ------------------------------------------------------------------
CHAINS: dict[str, Chain] = {
    "ethereum": Chain(
        name="ethereum", label="Ethereum", chain_id=1,
        tokens={
            "WETH": Token("WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
            "USDC": Token("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
            "USDT": Token("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
            "DAI":  Token("DAI",  "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
            "WBTC": Token("WBTC", "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
        },
        stables=["USDC", "USDT", "DAI"], mids=["WETH", "WBTC"],
        dexes=[
            Dex("UniswapV2", "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f", "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", 30),
            Dex("SushiSwap", "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac", "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", 30),
            Dex("PancakeV2", "0x1097053Fd2ea711dad45caCcc45EfF7548fCB362", "0xEfF92A263d31888d860bD50809A8D171709b7b1c", 25),
            Dex("ShibaSwap", "0x115934131916C8b277DD010Ee02de363c09d037c", "0x03f7724180AA6b939894B5Ca4314783B0b36b329", 30),
        ],
        aave_pool="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
        explorer="https://etherscan.io",
        rpc_env="FLASHSCAN_RPC",
        rpc_fallbacks=[
            "https://eth.llamarpc.com", "https://ethereum-rpc.publicnode.com",
            "https://rpc.ankr.com/eth", "https://eth.merkle.io",
        ],
    ),
    "base": Chain(
        name="base", label="Base", chain_id=8453,
        tokens={
            "WETH": Token("WETH", "0x4200000000000000000000000000000000000006", 18),
            "USDC": Token("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
            "DAI":  Token("DAI",  "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", 18),
        },
        stables=["USDC", "DAI"], mids=["WETH"],
        dexes=[
            Dex("UniswapV2", "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6", "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24", 30),
            Dex("BaseSwap",  "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB", "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86", 30),
            Dex("PancakeV2", "0x02a84c1b3BBD7401a5f7fa98a384EBC70bB5749E", "0x8cFe327CEc66d1C090Dd72bd0FF11d690C33a2Eb", 25),
        ],
        aave_pool="0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
        explorer="https://basescan.org",
        rpc_env="FLASHSCAN_RPC_BASE",
        rpc_fallbacks=[
            "https://mainnet.base.org", "https://base-rpc.publicnode.com", "https://base.llamarpc.com",
        ],
    ),
    "arbitrum": Chain(
        name="arbitrum", label="Arbitrum", chain_id=42161,
        tokens={
            "WETH": Token("WETH", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
            "USDC": Token("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
            "USDT": Token("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
            "DAI":  Token("DAI",  "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", 18),
            "WBTC": Token("WBTC", "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", 8),
        },
        stables=["USDC", "USDT", "DAI"], mids=["WETH"],
        dexes=[
            Dex("SushiSwap", "0xc35DADB65012eC5796536bD9864eD8773aBc74C4", "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506", 30),
            Dex("Camelot",   "0x6EcCab422D763aC031210895C81787E87B43A652", "0xc873fEcbd354f5A56E00E710B90EF4201db2448d", 30),
            Dex("UniswapV2", "0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9", "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24", 30),
        ],
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        explorer="https://arbiscan.io",
        rpc_env="FLASHSCAN_RPC_ARBITRUM",
        rpc_fallbacks=[
            "https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com", "https://arbitrum.llamarpc.com",
        ],
    ),
}

DEFAULT_CHAIN = "ethereum"


def get_chain(name: str | None) -> Chain:
    return CHAINS.get((name or DEFAULT_CHAIN).lower(), CHAINS[DEFAULT_CHAIN])


# --- Backward-compatible Ethereum aliases ------------------------------------
_eth = CHAINS["ethereum"]
TOKENS = _eth.tokens
STABLES = _eth.stables
MIDS = _eth.mids
DEXES = _eth.dexes
AAVE_V3_POOL = _eth.aave_pool
RPC_FALLBACKS = _eth.rpc_fallbacks


# --- Synthetic data for --demo (Ethereum only; no network) -------------------
@dataclass
class DemoPair:
    dex: str
    stable: str
    mid: str
    reserve_stable: int
    reserve_mid: int


DEMO_PAIRS = [
    DemoPair("UniswapV2", "USDC", "WETH", 60_000_000_000000, 30_000 * 10**18),      # 2,000 USD/WETH
    DemoPair("SushiSwap", "USDC", "WETH", 24_480_000_000000, 12_000 * 10**18),      # 2,040 USD/WETH (~2% off)
    DemoPair("UniswapV2", "DAI",  "WETH", 40_000_000 * 10**18, 20_000 * 10**18),    # 2,000 DAI/WETH
    DemoPair("SushiSwap", "DAI",  "WETH", 16_080_000 * 10**18, 8_000 * 10**18),     # 2,010 DAI/WETH (~0.5% off)
]
DEMO_ETH_USD = 2000.0
DEMO_GAS_PRICE_WEI = 8 * 10**9  # 8 gwei
