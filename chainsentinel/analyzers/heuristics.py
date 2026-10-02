"""Source-level heuristic scanner.

These regexes are PRE-FILTERS, not verdicts. They surface code regions that match
patterns associated with each exploit class so the AI reviewer (guided by the
matching skill) knows where to look. A hit is a lead, never a confirmed bug.
"""
from __future__ import annotations

import re

from .base import Finding
from ..taxonomy import Category


def _iter_files(files: dict[str, str]):
    for path, src in files.items():
        yield path, src


def run_heuristics(files: dict[str, str], categories: list[Category]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple] = set()

    for cat in categories:
        for h in cat.heuristics:
            pattern = h.get("pattern")
            if not pattern:
                continue
            note = h.get("note", "")
            try:
                rx = re.compile(pattern)
            except re.error:
                continue
            for path, src in _iter_files(files):
                for m in rx.finditer(src):
                    line = src.count("\n", 0, m.start()) + 1
                    key = (cat.id, pattern, path, line)
                    if key in seen:
                        continue
                    seen.add(key)
                    snippet = _line_at(src, line)
                    findings.append(
                        Finding(
                            category=cat.id,
                            title=f"{cat.name}: pattern `{pattern}`",
                            severity="informational",   # heuristic leads start as info
                            source="heuristic",
                            detail=note,
                            file=path,
                            line=line,
                            evidence=snippet,
                            skill=cat.skill,
                        )
                    )
    return findings


def _line_at(src: str, line: int) -> str:
    lines = src.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()[:200]
    return ""


def summarize_by_category(findings: list[Finding]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        out[f.category] = out.get(f.category, 0) + 1
    return out
