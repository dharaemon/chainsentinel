"""Load the exploit taxonomy from data/taxonomy.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "taxonomy.yaml"


@dataclass
class Category:
    id: str
    name: str
    skill: str
    default_severity: str
    subtypes: list[str]
    heuristics: list[dict]


def _require_yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "PyYAML is required to load the taxonomy.\n"
            "Install it with:  python3 -m pip install pyyaml"
        ) from e


def load(path: str | Path | None = None) -> list[Category]:
    yaml = _require_yaml()
    p = Path(path) if path else _DATA
    data = yaml.safe_load(p.read_text())
    cats = []
    for c in data.get("categories", []):
        cats.append(
            Category(
                id=c["id"],
                name=c["name"],
                skill=c.get("skill", ""),
                default_severity=c.get("default_severity", "medium"),
                subtypes=c.get("subtypes", []),
                heuristics=c.get("heuristics", []),
            )
        )
    return cats
