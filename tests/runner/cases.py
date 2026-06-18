"""Load and validate YAML test cases into typed objects.

Schema (see docs/testing.md):

    name: str (required, unique)
    description: str
    transport: unary | bidi | mock   (optional; default from config)
    session:
      variables: {k: v}              # data variables passed at session start
    turns:
      - user: str
        expect: [ {<assertion>: <value>}, ... ]
    final:
      expect: [ {<assertion>: <value>}, ... ]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Turn:
    user: str
    expect: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Case:
    name: str
    description: str = ""
    transport: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    turns: list[Turn] = field(default_factory=list)
    final_expect: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(f"Case in {self.source!r} is missing required 'name'.")
        if not self.turns:
            raise ValueError(f"Case {self.name!r} has no 'turns'.")


def _parse_case(raw: dict[str, Any], source: str) -> Case:
    session = raw.get("session") or {}
    turns = [
        Turn(user=t["user"], expect=t.get("expect", []) or [])
        for t in (raw.get("turns") or [])
    ]
    final = (raw.get("final") or {}).get("expect", []) or []
    return Case(
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        transport=raw.get("transport"),
        variables=session.get("variables", {}) or {},
        turns=turns,
        final_expect=final,
        source=source,
    )


def load_cases(cases_dir: Path, only: str | None = None) -> list[Case]:
    """Load all *.yaml cases from a directory (files starting with '_' are ignored)."""
    cases: list[Case] = []
    for path in sorted(cases_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue  # templates / partials
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw:
            continue
        case = _parse_case(raw, source=str(path))
        if only and case.name != only:
            continue
        cases.append(case)

    if only and not cases:
        raise ValueError(f"No case named {only!r} found in {cases_dir}.")
    return cases
