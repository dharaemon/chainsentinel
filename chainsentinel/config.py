"""Configuration: env vars, .env loading, and per-chain RPC overrides."""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | None = None) -> None:
    """Minimal .env loader (no external dependency).

    Looks for a .env in CWD or the given path. Existing environment variables
    always take precedence over .env values.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.append(Path.cwd() / ".env")
    for p in candidates:
        if not p.is_file():
            continue
        for raw in p.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)
        return


def explorer_api_key() -> str:
    """Etherscan V2 unified API key (works across chains).

    Falls back to legacy BscScan/Etherscan keys if set.
    """
    for var in ("ETHERSCAN_API_KEY", "CHAINSENTINEL_API_KEY", "BSCSCAN_API_KEY"):
        v = os.environ.get(var)
        if v:
            return v
    return ""


def rpc_override(chain_key: str) -> str | None:
    var = f"CHAINSENTINEL_RPC_{chain_key.upper().replace('-', '_')}"
    return os.environ.get(var)


def ai_provider_default() -> str:
    return os.environ.get("CHAINSENTINEL_AI", "claude")
