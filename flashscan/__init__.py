"""flashscan — honest cross-DEX flash-loan arbitrage scanner + simulator.

Read-only. It reads live DEX reserves, computes the best cross-DEX cycle for
each pair, and subtracts the Aave flash-loan premium, gas, and price impact to
show the REAL net. It never signs, deploys, or sends a transaction, and it does
not pretend a positive gross spread is yours to capture (see the honesty notes
surfaced in every result).
"""

__version__ = "0.1.0"
