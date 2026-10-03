"""Differential fuzzer driven by autoconf configs.

``fuzz_pair(A, B)``: flags whose configured values differ between A and B are
*known* divergences; their rules' ``fuzz.avoid`` features are excluded from
generation, so any remaining disagreement is new behavior. Hypothesis
``find`` shrinks it to a minimal example; the example database lives in
``fuzz-db/`` (checked in) and every finding is also written as readable JSON
under ``findings/<A>__<B>/`` with the rules it may be explained by.

``flipcheck(A, B)``: the key self-test. For each divergent flag, pretend A
agrees with B on it (a deliberately wrong config); the fuzzer must then find
an example carrying that flag's features.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time

from hypothesis import HealthCheck, Phase, find, settings
from hypothesis.database import DirectoryBasedExampleDatabase
from hypothesis.errors import NoSuchExample, Unsatisfiable

from .adapter import Adapter, Case
from .adapters import make
from .gen import example
from .rules import ROOT, Rule, load_rules
from .run import load_config, values

FINDINGS = ROOT / "findings"
DB = DirectoryBasedExampleDatabase(str(ROOT / "fuzz-db"))


def divergent(va: dict, vb: dict) -> set[str]:
    """Flags not known to agree. UNKNOWN/AMBIGUOUS count as divergent: an
    unexplained behavior must not leak into the fuzz space."""
    out = set()
    for f in set(va) | set(vb):
        a, b = va.get(f), vb.get(f)
        if a != b or a is None or a == "UNKNOWN" or str(a).startswith("AMBIGUOUS"):
            out.add(f)
    return out


def avoid_for(flags: set[str], rules: dict[str, Rule]) -> list[frozenset]:
    out = {c for f in flags if f in rules for c in rules[f].avoid}
    return sorted(out, key=lambda c: (len(c), sorted(c)))


def explain(features: frozenset, rules: dict[str, Rule]) -> list[str]:
    """Rules with an avoid conjunction fully present in this example."""
    return sorted(f for f, r in rules.items() if any(c <= features for c in r.avoid))


def _adapter(spec) -> Adapter:
    if isinstance(spec, Adapter):
        return spec
    name, _, opts = str(spec).partition(":")
    kw = dict(o.split("=", 1) for o in opts.split(",") if o) if opts else {}
    return make(name, **kw)


def _config_values(spec, adapter: Adapter) -> dict:
    if isinstance(spec, dict):
        return spec
    try:
        return values(load_config(adapter.name))
    except FileNotFoundError:
        from .run import autoconf

        return values(autoconf(adapter))


def fuzz_pair(a, b, *, max_examples=300, flips: dict | None = None, seed=None,
              va: dict | None = None, vb: dict | None = None, record=True) -> dict:
    """Search for a disagreement between adapters ``a`` and ``b`` outside
    their known divergences. ``flips`` overrides A's config values."""
    A, B = _adapter(a), _adapter(b)
    rules = {r.flag: r for r in load_rules()}
    va = dict(va if va is not None else _config_values(None, A))
    vb = vb if vb is not None else _config_values(None, B)
    va.update(flips or {})
    known = divergent(va, vb)
    avoid = avoid_for(known, rules)
    key = hashlib.sha256(f"{A.label()}|{B.label()}|{[sorted(c) for c in avoid]}".encode()).digest()

    def differs(ex):
        case, _ = ex
        return A.observe(case).text != B.observe(case).text

    t0 = time.time()
    opts = dict(max_examples=max_examples, database=DB if record else None, deadline=None,
                suppress_health_check=list(HealthCheck), phases=list(Phase))
    try:
        case, feats = find(example(avoid), differs, settings=settings(**opts), database_key=key,
                           random=None if seed is None else __import__("random").Random(seed))
    except (NoSuchExample, Unsatisfiable):
        return {"pair": [A.label(), B.label()], "known_divergent": len(known),
                "avoid": [sorted(c) for c in avoid], "finding": None, "seconds": round(time.time() - t0, 2)}
    oa, ob = A.observe(case), B.observe(case)
    finding = {
        "case": {"op": case.op, "query": case.query, "mol": case.mol,
                 "explicit_h": case.explicit_h, "view": case.view},
        "observed": {A.label(): oa.text, B.label(): ob.text},
        "detail": {A.label(): oa.detail[:200], B.label(): ob.detail[:200]},
        "features": sorted(feats),
        "explained_by": explain(feats, rules),
    }
    out = {"pair": [A.label(), B.label()], "known_divergent": len(known), "avoid": [sorted(c) for c in avoid],
           "finding": finding, "seconds": round(time.time() - t0, 2)}
    if record:
        out["file"] = str(write_finding(A, B, finding).relative_to(ROOT))
    return out


def write_finding(A: Adapter, B: Adapter, finding: dict):
    c = finding["case"]
    h = hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:10]
    p = FINDINGS / f"{A.label()}__{B.label()}" / f"{h}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"found": dt.date.today().isoformat(),
           "versions": {A.label(): A.version(), B.label(): B.version()}, **finding,
           "status": "explained" if finding["explained_by"] else "NEW: add a rule or extend one"}
    p.write_text(json.dumps(rec, indent=1) + "\n")
    return p


def replay(path) -> dict:
    """Re-observe a recorded finding on its adapters (regression check)."""
    rec = json.loads(open(path).read())
    case = Case("replay", **rec["case"])
    return {label: _adapter(label.split("[")[0]).observe(case).text for label in rec["observed"]}


def flipcheck(a, b, *, max_examples=300, flags=None, va=None, vb=None, verbose=True) -> list[dict]:
    """For each flag where A and B differ, set A's value to B's and fuzz.
    ``rediscovered`` = the shrunk example carries that flag's avoid features."""
    A, B = _adapter(a), _adapter(b)
    rules = {r.flag: r for r in load_rules()}
    va = va if va is not None else _config_values(None, A)
    vb = vb if vb is not None else _config_values(None, B)
    rows = []
    for f in sorted(divergent(va, vb)):
        if flags and f not in flags:
            continue
        if f not in rules or vb.get(f) in (None, "UNKNOWN") or str(vb.get(f)).startswith("AMBIG"):
            continue
        res = fuzz_pair(A, B, max_examples=max_examples, flips={f: vb[f]}, va=va, vb=vb, record=False)
        fd = res["finding"]
        still = {frozenset(c) for c in res["avoid"]}
        masked = all(any(o <= c for o in still) for c in rules[f].avoid)
        row = {"flag": f, "seconds": res["seconds"], "masked": masked,
               "rediscovered": bool(fd) and f in fd["explained_by"],
               "example": fd and fd["case"], "observed": fd and fd["observed"],
               "explained_by": fd and fd["explained_by"]}
        rows.append(row)
        if verbose:
            tag = "MASKED" if masked else ("ok" if row["rediscovered"] else "MISS")
            ex = fd and f"{fd['case']['query']} on {fd['case']['mol']}"
            print(f"{tag:6s} {f:42s} {res['seconds']:6.1f}s  {ex}")
    return rows
