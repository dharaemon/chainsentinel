"""flashscan.execution — honest, loss-safe flash-loan arbitrage execution layer.

Contract: flashscan/contracts/ArbitrageExecutor.sol
Keeper:   this package (scan -> build route -> simulate -> submit via Flashbots)

Dry-run by default. It can only ever TRY a trade; the on-chain invariant makes a
losing trade revert, so the worst case is a reverted tx that cost only gas.
See README.md in this directory.
"""
