"""The audit pipeline.

Order (as specified): resolve proxy FIRST, then run every check against the
resolved implementation.

  1. Connect RPC + explorer for the chosen chain.
  2. Detect proxy -> resolve implementation.
  3. Fetch verified source for the audited address (implementation if proxy).
  4. Run heuristic scan (taxonomy) + optional Slither.
  5. Build evidence bundle + AI prompt.
  6. Optionally invoke the AI reviewer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import proxy as proxy_mod
from .analyzers import run_heuristics, run_slither, slither_available
from .chains import Chain
from .explorer import Explorer
from .rpc import RpcClient
from .taxonomy import Category


@dataclass
class AuditContext:
    chain: Chain
    address: str
    api_key: str
    rpc_url: str
    categories: list[Category]
    use_slither: bool = True
    progress: object = None    # optional callable(str)

    def log(self, msg: str):
        if callable(self.progress):
            self.progress(msg)


def run_audit(ctx: AuditContext) -> dict:
    rpc = RpcClient(ctx.rpc_url)
    explorer = Explorer(ctx.chain.explorer_api, ctx.chain.chain_id, ctx.api_key)

    addr = ctx.address

    # --- Step 1: proxy FIRST -------------------------------------------------
    ctx.log("Step 1/5  Detecting proxy pattern...")
    pr = proxy_mod.detect(rpc, addr)
    audited_address = addr
    if pr.is_proxy and pr.implementation:
        audited_address = pr.implementation
        ctx.log(f"          Proxy = {pr.proxy_type}; implementation = {pr.implementation}")
    elif pr.is_proxy:
        ctx.log(f"          Proxy = {pr.proxy_type}; implementation UNRESOLVED")
    else:
        ctx.log("          No proxy; auditing address directly.")

    # --- Step 2: fetch verified source --------------------------------------
    ctx.log(f"Step 2/5  Fetching verified source for {audited_address} ...")
    src = explorer.get_source(audited_address)
    # If explorer itself flags a proxy with an implementation we missed, follow it.
    if (not pr.is_proxy) and src.proxy_flag == "1" and src.implementation:
        ctx.log(f"          Explorer flags proxy -> implementation {src.implementation}; refetching.")
        pr.is_proxy = True
        pr.proxy_type = "Explorer-flagged proxy"
        pr.implementation = src.implementation
        audited_address = src.implementation
        src = explorer.get_source(audited_address)

    source_files = src.files if src.verified else {}
    meta_notes = list(src.notes)
    if not src.verified:
        meta_notes.append(
            "Source NOT verified: heuristic/Slither coverage is unavailable. "
            "Consider bytecode decompilation (e.g. Dedaub, heimdall) before AI review."
        )

    # --- Step 3: heuristics --------------------------------------------------
    ctx.log("Step 3/5  Running taxonomy heuristics...")
    findings = []
    if source_files:
        findings += run_heuristics(source_files, ctx.categories)

    # --- Step 4: Slither (optional) -----------------------------------------
    slither_ran = False
    if ctx.use_slither and source_files:
        if slither_available():
            ctx.log("Step 4/5  Running Slither static analysis...")
            sl_findings, sl_notes = run_slither(source_files, src.compiler_version)
            findings += sl_findings
            meta_notes += sl_notes
            slither_ran = True
        else:
            ctx.log("Step 4/5  Slither not installed - skipping (heuristics only).")
            meta_notes.append("Slither not installed; install for deeper static analysis.")
    else:
        ctx.log("Step 4/5  Slither disabled or no source - skipping.")

    # --- Step 5: assemble bundle --------------------------------------------
    ctx.log("Step 5/5  Assembling evidence bundle...")
    bundle = {
        "meta": {
            "chain": ctx.chain.name,
            "chain_key": ctx.chain.key,
            "chain_id": ctx.chain.chain_id,
            "address": addr,
            "audited_address": audited_address,
            "explorer_web": ctx.chain.explorer_web,
            "verified": src.verified,
            "contract_name": src.contract_name,
            "compiler_version": src.compiler_version,
            "slither_ran": slither_ran,
            "notes": meta_notes,
        },
        "proxy": pr.to_dict(),
        "findings": [f.to_dict() for f in findings],
        "source_files": source_files,
    }
    return bundle
