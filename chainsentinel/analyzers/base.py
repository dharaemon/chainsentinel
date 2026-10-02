"""Shared finding type."""
from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "informational": 4,
}


@dataclass
class Finding:
    category: str            # taxonomy category id
    title: str
    severity: str            # critical|high|medium|low|informational
    source: str              # which analyzer produced it: "heuristic" | "slither" | "ai"
    detail: str = ""
    file: str = ""
    line: int | None = None
    evidence: str = ""       # code snippet or matched text
    skill: str = ""          # skill file that should be used to confirm/deepen

    def sort_key(self):
        return (SEVERITY_ORDER.get(self.severity, 9), self.category)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "title": self.title,
            "severity": self.severity,
            "source": self.source,
            "detail": self.detail,
            "file": self.file,
            "line": self.line,
            "evidence": self.evidence,
            "skill": self.skill,
        }
