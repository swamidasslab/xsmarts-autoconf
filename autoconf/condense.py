"""Condense configs + rules into human reports and targeted test cases."""

from __future__ import annotations

from .adapters import ADAPTERS
from .rules import Rule, load_rules
from .run import load_config


def _cfg(spec):
    return spec if isinstance(spec, dict) else load_config(spec)


def distinguishing_case(rule: Rule, a: str, b: str):
    """First case whose expectations differ between values ``a`` and ``b``."""
    for c in rule.cases:
        ea, eb = rule.expect[c.id].get(a, "*"), rule.expect[c.id].get(b, "*")
        if ea != eb and "*" not in (ea, eb):
            return c, ea, eb
    return None


def _case_text(c) -> str:
    extra = []
    if c.explicit_h:
        extra.append("explicit H")
    if c.view != "products":
        extra.append(f"view={c.view}")
    tail = f" ({', '.join(extra)})" if extra else ""
    return f"`{c.query}`" + (f" on `{c.mol}`" if c.mol else "") + f" [{c.op}]{tail}"


def report(specs) -> str:
    cfgs = [_cfg(s) for s in specs if not isinstance(s, str) or s not in ADAPTERS or _has(s)]
    rules = {r.flag: r for r in load_rules()}
    labels = [c["label"] for c in cfgs]
    out = ["# Autoconf report", "",
           "| adapter | version | options | rules digest |", "|---|---|---|---|"]
    out += [f"| {c['label']} | {c['version']} | {c['options'] or ''} | {c['rules_digest']} |" for c in cfgs]
    out += ["", "## Flag values", "", "| flag | " + " | ".join(labels) + " |",
            "|---|" + "---|" * len(labels)]
    for f in rules:
        vals = [c["flags"].get(f, {}).get("value", "-") for c in cfgs]
        mark = "" if len(set(vals)) == 1 else " **≠**"
        out.append(f"| `{f}`{mark} | " + " | ".join(vals) + " |")
    out += ["", "## Divergent flags", ""]
    for f, r in rules.items():
        vals = {c["label"]: c["flags"].get(f, {}).get("value") for c in cfgs}
        distinct = sorted({v for v in vals.values() if v and v in r.values})
        if len(distinct) < 2:
            continue
        out += [f"### `{f}`", "", r.summary, ""]
        for v in distinct:
            who = ", ".join(k for k, x in vals.items() if x == v)
            out.append(f"- **{v}** ({who}): {r.values[v]}")
        d = distinguishing_case(r, distinct[0], distinct[1])
        if d:
            c, ea, eb = d
            out += ["", f"Minimal example: {_case_text(c)}: `{distinct[0]}` → `{ea}`, `{distinct[1]}` → `{eb}`"]
        if r.processing:
            out += ["", f"Processing: {r.processing}"]
        prov = r.provenance.get("discovered")
        if prov:
            out += ["", f"Discovered: {prov}"]
        out.append("")
    return "\n".join(out) + "\n"


def _has(name) -> bool:
    try:
        load_config(name)
        return True
    except FileNotFoundError:
        return False


def target_tests(spec, like) -> dict:
    """Cases that move the library in ``spec`` to the behavior of ``like``.

    For every flag where they differ, each case where the target value pins an
    outcome: input, what the library does now, what the target expects, and
    the rule's description of both behaviors. Feed these to the library's
    test suite or to an emulation layer."""
    cfg, tgt = _cfg(spec), _cfg(like)
    rules = {r.flag: r for r in load_rules()}
    tests = []
    for f, r in rules.items():
        have, want = cfg["flags"].get(f, {}).get("value"), tgt["flags"].get(f, {}).get("value")
        if have == want or want not in r.values:
            continue
        for c in r.cases:
            exp = r.expect[c.id].get(want, "*")
            now = cfg["flags"][f]["observed"].get(c.id)
            if exp == "*":
                continue
            tests.append({
                "flag": f, "case": c.id, "op": c.op, "query": c.query, "mol": c.mol,
                "explicit_h": c.explicit_h, "view": c.view,
                "current": {"value": have, "observed": now, "means": r.values.get(have, "")},
                "target": {"value": want, "expected": exp, "means": r.values[want]},
            })
    return {"library": cfg["label"], "version": cfg["version"],
            "target": tgt["label"], "target_version": tgt["version"],
            "n_flags": len({t["flag"] for t in tests}), "tests": tests}
