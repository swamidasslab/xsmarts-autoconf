"""Rule files: ``rules/<area>/<flag>.json``, one feature flag per file.

Schema (see README for the annotated version)::

    {
      "flag": "match.ring_size_semantics",
      "summary": "what the flag distinguishes",
      "values": {"smallest_ring": "description", "any_ring": "description"},
      "cases": [
        {"id": "r6_on_hydrindane_bridgehead", "op": "match",
         "query": "[r6]", "mol": "C1CCC2CCCC2C1", "explicit_h": false,
         "expect": {"smallest_ring": "match:4", "any_ring": "match:6"}}
      ],
      "provenance": {"discovered": "...", "refs": ["docs/..."]},
      "processing": "pre/post-processing notes (AddHs, sanitize, H mode)",
      "fuzz": {"avoid": ["ring.fused"]}
    }

A value is *selected* when every case's observation satisfies that value's
expectation. Expectation patterns: an exact observation string, ``*`` (any),
``match:+`` (at least one match), ``re:<regex>``, or a list of alternatives.
A case with no entry for a value does not constrain it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .adapter import Case

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"


@dataclass
class Rule:
    flag: str
    summary: str
    values: dict[str, str]
    cases: list[Case]
    expect: dict[str, dict[str, object]]
    """case id -> value -> pattern"""
    provenance: dict = field(default_factory=dict)
    processing: str = ""
    avoid: list[str] = field(default_factory=list)
    path: Path | None = None

    @property
    def area(self) -> str:
        return self.flag.split(".", 1)[0]

    def consistent(self, observed: dict[str, str]) -> list[str]:
        """Values whose expectations every observed case satisfies."""
        return [v for v in self.values
                if all(satisfies(self.expect[c.id].get(v, "*"), observed[c.id])
                       for c in self.cases if c.id in observed)]

    def resolve(self, observed: dict[str, str]) -> str:
        """The selected value, ``n/a`` if every case was unsupported,
        ``UNKNOWN`` (new behavior: no value fits) or ``AMBIGUOUS:a|b``."""
        if observed and all(t == "unsupported" for t in observed.values()):
            return "n/a"
        ok = self.consistent(observed)
        if len(ok) == 1:
            return ok[0]
        return "UNKNOWN" if not ok else "AMBIGUOUS:" + "|".join(ok)

    def expected(self, value: str) -> dict[str, object]:
        return {c.id: self.expect[c.id].get(value, "*") for c in self.cases}


def satisfies(pattern: object, text: str) -> bool:
    if isinstance(pattern, list):
        return any(satisfies(p, text) for p in pattern)
    assert isinstance(pattern, str)
    if pattern == "*":
        return True
    if pattern == "match:+":
        return text.startswith("match:") and int(text[6:]) > 0
    if pattern.startswith("re:"):
        return re.fullmatch(pattern[3:], text) is not None
    return pattern == text


_CASE_FIELDS = {"id", "op", "query", "mol", "explicit_h", "view", "note", "orderings", "spellings", "fixed_spelling"}


def load_rule(path: Path) -> Rule:
    d = json.loads(path.read_text())
    cases, expect = [], {}
    for c in d["cases"]:
        kw = {k: v for k, v in c.items() if k in _CASE_FIELDS}
        if "spellings" in kw:
            kw["spellings"] = tuple(kw["spellings"])
        cases.append(Case(**kw))
        expect[c["id"]] = c.get("expect", {})
        unknown = set(expect[c["id"]]) - set(d["values"])
        if unknown:
            raise ValueError(f"{path}: case {c['id']} expects undeclared values {unknown}")
    if len({c.id for c in cases}) != len(cases):
        raise ValueError(f"{path}: duplicate case ids")
    return Rule(d["flag"], d.get("summary", ""), d["values"], cases, expect,
                d.get("provenance", {}), d.get("processing", ""),
                d.get("fuzz", {}).get("avoid", []), path)


def load_rules(root: Path = RULES_DIR, flags: list[str] | None = None) -> list[Rule]:
    rules = [load_rule(p) for p in sorted(root.rglob("*.json"))]
    seen = set()
    for r in rules:
        if r.flag in seen:
            raise ValueError(f"duplicate flag {r.flag}")
        seen.add(r.flag)
    if flags is not None:
        rules = [r for r in rules if r.flag in flags]
    return rules


def rules_digest(root: Path = RULES_DIR) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.json")):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]
