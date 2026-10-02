"""Optional Slither integration.

If `slither` (https://github.com/crytic/slither) is installed, we run it over the
fetched source and fold its results into the findings list. If it is absent, the
audit still runs on heuristics + AI review; we just note the capability gap.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import Finding

# Map Slither's check impact to our severity scale.
_IMPACT = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Informational": "informational",
    "Optimization": "informational",
}

# Rough mapping of common Slither detector ids -> our taxonomy categories.
_CHECK_TO_CATEGORY = {
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy",
    "reentrancy-events": "reentrancy",
    "arbitrary-send-eth": "access-control",
    "suicidal": "access-control",
    "unprotected-upgrade": "proxy-upgradeability",
    "tx-origin": "access-control",
    "incorrect-equality": "business-logic",
    "weak-prng": "randomness",
    "unchecked-transfer": "token-standard",
    "unchecked-lowlevel": "external-call",
    "unchecked-send": "external-call",
    "controlled-delegatecall": "access-control",
    "delegatecall-loop": "external-call",
    "divide-before-multiply": "arithmetic",
    "uninitialized-state": "state-storage",
    "uninitialized-storage": "state-storage",
    "locked-ether": "dos",
    "calls-loop": "dos",
    "timestamp": "business-logic",
}


def slither_available() -> bool:
    return shutil.which("slither") is not None


def run_slither(files: dict[str, str], compiler_version: str = "") -> tuple[list[Finding], list[str]]:
    notes: list[str] = []
    if not slither_available():
        notes.append("Slither not installed - skipping static analysis. "
                     "Install: python3 -m pip install slither-analyzer (needs solc).")
        return [], notes

    findings: list[Finding] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for path, src in files.items():
            fp = root / path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(src)
        out_json = root / "slither.json"
        cmd = ["slither", str(root), "--json", str(out_json)]
        try:
            subprocess.run(cmd, cwd=td, capture_output=True, text=True, timeout=600)
        except (subprocess.TimeoutExpired, OSError) as e:
            notes.append(f"Slither run failed: {e}")
            return [], notes

        if not out_json.is_file():
            notes.append("Slither produced no JSON output (compile error?). "
                         "Try auditing with the exact solc version "
                         f"'{compiler_version}' installed via solc-select.")
            return [], notes
        try:
            data = json.loads(out_json.read_text())
        except json.JSONDecodeError:
            notes.append("Could not parse Slither JSON output.")
            return [], notes

    for det in data.get("results", {}).get("detectors", []):
        check = det.get("check", "")
        severity = _IMPACT.get(det.get("impact", ""), "informational")
        category = _CHECK_TO_CATEGORY.get(check, "business-logic")
        file = ""
        line = None
        for el in det.get("elements", []):
            sm = el.get("source_mapping", {})
            if sm.get("filename_relative"):
                file = sm["filename_relative"]
                lines = sm.get("lines") or []
                line = lines[0] if lines else None
                break
        findings.append(
            Finding(
                category=category,
                title=f"Slither: {check}",
                severity=severity,
                source="slither",
                detail=det.get("description", "").strip(),
                file=file,
                line=line,
                evidence="",
                skill="",
            )
        )
    return findings, notes
