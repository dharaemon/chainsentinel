"""ChainSentinel command-line interface.

Usage:
  chainsentinel audit <address> [--chain bsc] [--ai claude|codex|openai|none]
  chainsentinel proxy <address> [--chain bsc]
  chainsentinel chains
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import __version__
from . import ai_bridge, report
from .chains import CHAINS, get_chain
from .config import (
    ai_provider_default,
    explorer_api_key,
    load_dotenv,
    rpc_override,
)
from .orchestrator import AuditContext, run_audit
from .proxy import detect as detect_proxy
from .rpc import RpcClient
from .taxonomy import load as load_taxonomy

ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _eprint(msg: str):
    print(msg, file=sys.stderr)


def _validate_address(address: str) -> str:
    if not ADDR_RE.match(address):
        _eprint(f"error: '{address}' is not a valid 0x-prefixed 20-byte address.")
        raise SystemExit(2)
    return address


def cmd_chains(_args) -> int:
    print("Supported chains:")
    for key, c in CHAINS.items():
        print(f"  {key:14s} id={c.chain_id:<6d} {c.name}  ({c.explorer_web})")
    return 0


def cmd_proxy(args) -> int:
    chain = get_chain(args.chain)
    addr = _validate_address(args.address)
    rpc_url = args.rpc or rpc_override(chain.key) or chain.rpc
    rpc = RpcClient(rpc_url)
    print(f"Checking proxy for {addr} on {chain.name} via {rpc_url} ...")
    pr = detect_proxy(rpc, addr)
    if pr.is_proxy:
        print(f"  Proxy: YES ({pr.proxy_type})")
        print(f"  Implementation: {pr.implementation}")
        if pr.admin:
            print(f"  Admin: {pr.admin}")
        if pr.beacon:
            print(f"  Beacon: {pr.beacon}")
    else:
        print("  Proxy: no")
    for n in pr.notes:
        print(f"    - {n}")
    return 0


def cmd_audit(args) -> int:
    chain = get_chain(args.chain)
    addr = _validate_address(args.address)
    api_key = explorer_api_key()
    rpc_url = args.rpc or rpc_override(chain.key) or chain.rpc

    if not api_key:
        _eprint("warning: no explorer API key set (ETHERSCAN_API_KEY). "
                "Public rate limits apply and some requests may fail.")

    categories = load_taxonomy()

    ctx = AuditContext(
        chain=chain,
        address=addr,
        api_key=api_key,
        rpc_url=rpc_url,
        categories=categories,
        use_slither=not args.no_slither,
        progress=_eprint,
    )

    bundle = run_audit(ctx)

    # Build the AI prompt bundle regardless of whether we call a model live.
    prompt = ai_bridge.build_prompt(bundle)

    provider = args.ai or ai_provider_default()
    ai_output = None
    if provider and provider.lower() != "none":
        _eprint(f"Invoking AI reviewer: {provider} ...")
        try:
            ai_output = ai_bridge.review(prompt, provider)
        except Exception as e:  # noqa: BLE001 - surface any provider failure cleanly
            _eprint(f"AI review skipped ({e}). Prompt bundle still written to disk.")

    # Output files
    outdir = Path(args.out or ".")
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"chainsentinel_{chain.key}_{addr[:10]}"

    md = report.to_markdown(bundle, ai_output)
    js = report.to_json(bundle, ai_output)

    (outdir / f"{stem}.report.md").write_text(md)
    (outdir / f"{stem}.report.json").write_text(js)
    (outdir / f"{stem}.prompt.md").write_text(prompt)

    print(f"\nReports written to {outdir}/:")
    print(f"  {stem}.report.md      (human-readable)")
    print(f"  {stem}.report.json    (machine-readable)")
    print(f"  {stem}.prompt.md      (AI prompt bundle - paste into any assistant)")

    if args.print:
        print("\n" + "=" * 70 + "\n")
        print(md)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chainsentinel",
        description="AI-assisted static auditor for public smart contracts (read-only).",
    )
    p.add_argument("--version", action="version", version=f"ChainSentinel {__version__}")
    p.add_argument("--env", help="path to a .env file", default=None)
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("audit", help="full audit pipeline for a contract address")
    pa.add_argument("address", help="0x contract address")
    pa.add_argument("--chain", default="bsc", help="chain key (default: bsc)")
    pa.add_argument("--ai", default=None,
                    help="AI provider: claude|codex|openai|none (default: env CHAINSENTINEL_AI or claude)")
    pa.add_argument("--rpc", default=None, help="override RPC URL")
    pa.add_argument("--out", default=None, help="output directory (default: cwd)")
    pa.add_argument("--no-slither", action="store_true", help="skip Slither even if installed")
    pa.add_argument("--print", action="store_true", help="print the markdown report to stdout")
    pa.set_defaults(func=cmd_audit)

    pp = sub.add_parser("proxy", help="only detect/resolve proxy for an address")
    pp.add_argument("address", help="0x contract address")
    pp.add_argument("--chain", default="bsc", help="chain key (default: bsc)")
    pp.add_argument("--rpc", default=None, help="override RPC URL")
    pp.set_defaults(func=cmd_proxy)

    pc = sub.add_parser("chains", help="list supported chains")
    pc.set_defaults(func=cmd_chains)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_dotenv(args.env)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
