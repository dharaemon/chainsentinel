"""Render audit results to Markdown and JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .analyzers.base import Finding, SEVERITY_ORDER

_BADGE = {
    "critical": "🔴 CRITICAL",
    "high": "🟠 HIGH",
    "medium": "🟡 MEDIUM",
    "low": "🔵 LOW",
    "informational": "⚪ INFO",
}


def to_json(bundle: dict, ai_output: str | None) -> str:
    out = dict(bundle)
    out["ai_review"] = ai_output or ""
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    return json.dumps(out, indent=2)


def to_markdown(bundle: dict, ai_output: str | None) -> str:
    meta = bundle["meta"]
    proxy = bundle["proxy"]
    findings = [Finding(**{k: f[k] for k in (
        "category", "title", "severity", "source", "detail", "file", "line", "evidence", "skill"
    )}) for f in bundle["findings"]]
    findings.sort(key=lambda f: f.sort_key())

    lines = []
    lines.append(f"# ChainSentinel Audit Report")
    lines.append("")
    lines.append(f"- **Chain:** {meta['chain']} (id {meta['chain_id']})")
    lines.append(f"- **Address:** `{meta['address']}`")
    lines.append(f"- **Explorer:** {meta['explorer_web']}/address/{meta['address']}")
    lines.append(f"- **Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- **Tool:** ChainSentinel (read-only static + AI-assisted review)")
    lines.append("")

    lines.append("## 1. Proxy resolution (first step)")
    lines.append("")
    if proxy["is_proxy"]:
        lines.append(f"- **Proxy detected:** yes — {proxy['proxy_type']}")
        lines.append(f"- **Implementation:** `{proxy.get('implementation')}`")
        if proxy.get("admin"):
            lines.append(f"- **Admin (upgrade authority):** `{proxy['admin']}`")
        if proxy.get("beacon"):
            lines.append(f"- **Beacon:** `{proxy['beacon']}`")
        lines.append("- Logic checks below were pointed at the **implementation**; "
                     "storage & upgrade authority remain on the proxy.")
    else:
        lines.append("- **Proxy detected:** no (audited the address directly).")
    for n in proxy.get("notes", []):
        lines.append(f"  - _{n}_")
    lines.append("")

    lines.append("## 2. Metadata")
    lines.append("")
    lines.append(f"- Verified source: **{meta.get('verified')}**")
    lines.append(f"- Contract name: {meta.get('contract_name','')}")
    lines.append(f"- Compiler: {meta.get('compiler_version','')}")
    lines.append(f"- Slither: {'ran' if meta.get('slither_ran') else 'not run'}")
    for n in meta.get("notes", []):
        lines.append(f"- _{n}_")
    lines.append("")

    # Severity rollup
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    lines.append("## 3. Findings summary")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    for sev in sorted(counts, key=lambda s: SEVERITY_ORDER.get(s, 9)):
        lines.append(f"| {_BADGE.get(sev, sev)} | {counts[sev]} |")
    lines.append("")
    lines.append("> Heuristic leads are **starting points**, not confirmed bugs. "
                 "The AI review section adjudicates them.")
    lines.append("")

    lines.append("## 4. Detailed leads")
    lines.append("")
    lines.append("| Severity | Category | Source | Location | Detail | Skill |")
    lines.append("|---|---|---|---|---|---|")
    for f in findings:
        loc = f"{f.file}:{f.line}" if f.file else "-"
        detail = (f.detail or f.title).replace("|", "\\|")[:120]
        lines.append(
            f"| {_BADGE.get(f.severity, f.severity)} | {f.category} | {f.source} "
            f"| `{loc}` | {detail} | {f.skill or '-'} |"
        )
    lines.append("")

    lines.append("## 5. AI auditor review")
    lines.append("")
    if ai_output:
        lines.append(ai_output)
    else:
        lines.append("_No live AI review was run. Use `--ai claude|codex|openai`, "
                     "or paste the generated prompt bundle (`*.prompt.md`) into your assistant._")
    lines.append("")

    lines.append("---")
    lines.append("_ChainSentinel is an assistive tool. Confirm every finding manually "
                 "before acting. It performs no transactions and gives no financial advice._")
    return "\n".join(lines)
