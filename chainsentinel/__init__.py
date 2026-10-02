"""ChainSentinel - AI-assisted static auditor for public smart contracts.

Read-only by design: it fetches public source/bytecode and chain state, runs
heuristic + static analysis, and prepares an evidence bundle for an AI reviewer.
It never signs, deploys, or sends transactions.
"""

__version__ = "0.1.0"
