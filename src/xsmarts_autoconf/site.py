"""Build the static comparison site from checked-in rules and configs.

``xsmarts-autoconf site --out _site`` copies ``site/`` (HTML/JS/CSS) and writes
``data.json``: every rule (summary, values, cases), every stored config
(one per library version) and the per-value severities in
``data/site/severity.json``. Standard library only, so CI needs no chemistry.

Reference engines (``pyref``, ``xenosmarts``) are left out unless
``--include-reference``: they are configurable emulators, not libraries
people choose between.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

from .rules import DATA, RULES_DIR

REFERENCE = {"pyref", "xenosmarts"}
# BioTransformer matches and parses with the CDK in its jar: one vote, not two.
SHARED_ENGINE = {("biotransformer", "match"): "cdk", ("biotransformer", "syntax"): "cdk"}
STATIC = Path(__file__).resolve().parents[2] / "site"


def _configs(include_reference: bool) -> list[dict]:
    out = []
    for f in sorted((DATA / "configs").glob("*/*.json")):
        c = json.loads(f.read_text())
        if c["adapter"] in REFERENCE and not include_reference:
            continue
        out.append({
            "id": f"{c['adapter']}@{c['version']}",
            "adapter": c["adapter"],
            "version": c["version"],
            "generated": c.get("generated"),
            "flags": {k: {"value": v["value"], "observed": v.get("observed", {})}
                      for k, v in c["flags"].items()},
        })
    return out


def _consensus(configs: list[dict], severity: dict) -> dict[str, str | None]:
    """Most common non-bug value per flag, one vote per library (its newest
    config). A bug shared by most libraries is still a bug, never green."""
    newest: dict[str, dict] = {}
    for c in configs:
        newest[c["adapter"]] = c  # sorted by path; last version wins
    votes: dict[str, dict[str, str]] = {}
    for c in newest.values():
        for flag, v in c["flags"].items():
            voter = SHARED_ENGINE.get((c["adapter"], flag.split(".")[0]), c["adapter"])
            bug = severity.get(flag, {}).get(v["value"]) == "bug"
            if v["value"] not in ("UNKNOWN", "AMBIGUOUS") and not bug:
                votes.setdefault(flag, {})[voter] = v["value"]
    out = {}
    for flag, by_voter in votes.items():
        cnt = Counter(by_voter.values())
        (top, n), *rest = cnt.most_common() + [(None, 0)]
        # a strict plurality (ties leave the flag without a consensus)
        out[flag] = top if rest[0][1] < n else None
    return out


def build(out: Path, include_reference: bool = False) -> Path:
    rules = [json.loads(f.read_text()) for f in sorted(RULES_DIR.glob("*/*.json"))]
    configs = _configs(include_reference)
    severity = json.loads((DATA / "site" / "severity.json").read_text())["values"]
    data = {
        "rules": [{
            "flag": r["flag"],
            "area": r["flag"].split(".")[0],
            "summary": r.get("summary", ""),
            "values": r["values"],
            "processing": r.get("processing"),
            "provenance": r.get("provenance"),
            "cases": [{k: c[k] for k in ("id", "op", "query", "mol", "view", "explicit_h", "note", "expect")
                       if k in c} for c in r["cases"]],
        } for r in rules],
        "configs": configs,
        "severity": severity,
        "consensus": _consensus(configs, severity),
    }
    if not STATIC.is_dir():
        raise SystemExit(f"static site sources not found at {STATIC} (run from a repo checkout)")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(STATIC, out)
    (out / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    return out


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="xsmarts-autoconf site")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--include-reference", action="store_true")
    a = ap.parse_args(argv)
    p = build(Path(a.out), a.include_reference)
    print(f"site written to {p}/ (open {p}/index.html via a local server, e.g. python -m http.server -d {p})")
    return 0
