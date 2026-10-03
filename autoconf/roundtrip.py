"""Round trip: config -> configured engine -> autoconf -> same config.

Engines that can be configured from autoconf flags expose a table
``{flag: (engine field, {value: setting})}`` and ``from_config``:
``PyRef`` (smarts_grammar Profile) and ``Xenosmarts`` (Rust engine profile
flags). Two modes:

- ``unblinded``: per flag and value, configure only that flag and run only
  its rule. Fast, isolates each wire.
- ``blinded``: Hypothesis draws whole configs, runs the full rule set, and
  compares every wired flag. Catches flags that interact (one engine field
  moving another flag's outcome) and rules that read the wrong field.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from .adapters import PYREF_FLAGS, XENOSMARTS_FLAGS, PyRef, Xenosmarts
from .rules import load_rules
from .run import autoconf, values

ENGINES = {
    "pyref": (PyRef, PYREF_FLAGS),
    "xenosmarts": (Xenosmarts, XENOSMARTS_FLAGS),
}

# Known engine-field implications: (fields that must all hold, flag, value it forces).
# Found by the blinded round trip; declared so they are documented, not hidden.
IMPLIES = {
    "xenosmarts": [({"kekule_match": True}, "match.compound_bond_kekule", "kekule_order")],
}


def unblinded(engines=None, verbose=True) -> bool:
    rules = {r.flag: r for r in load_rules()}
    ok = True
    for name in engines or ENGINES:
        cls, table = ENGINES[name]
        for flag, (field, vals) in table.items():
            for value in vals:
                got = values(autoconf(cls.from_config({flag: value}), [rules[flag]]))[flag]
                good = got == value
                ok &= good
                if verbose:
                    print(f"{'ok  ' if good else 'FAIL'} {name:10s} {flag:38s} {field}={vals[value]!s:5s} "
                          f"want {value:18s} got {got}")
    return ok


def expected_flags(table, fields: dict[str, bool], implies=()) -> dict[str, str]:
    """Engine settings -> the flag values autoconf should report. Several
    flags may read one field (coupled flags); they move together.
    ``implies`` overrides flags forced by a combination of fields."""
    out = {}
    for flag, (field, vals) in table.items():
        out[flag] = next(v for v, setting in vals.items() if setting == fields[field])
    for cond, flag, value in implies:
        if all(fields.get(k) == v for k, v in cond.items()):
            out[flag] = value
    return out


def blinded(n: int = 20, engines=None, verbose=True) -> bool:
    """Draw engine *settings* (not flag values), so coupled flags stay
    consistent; run every rule; compare all wired flags."""
    rules = load_rules()
    failures = []
    for name in engines or ENGINES:
        cls, table = ENGINES[name]
        fields = sorted({f for f, _ in table.values()})
        strategy = st.fixed_dictionaries({f: st.booleans() for f in fields})

        @settings(max_examples=n, deadline=None, database=None, suppress_health_check=list(HealthCheck))
        @given(strategy)
        def check(setting):
            want = expected_flags(table, setting, IMPLIES.get(name, ()))
            got = values(autoconf(cls(options=dict(setting)), rules))
            bad = {f: (want[f], got[f]) for f in want if got[f] != want[f]}
            if bad:
                failures.append((name, setting, bad))

        check()
    if verbose:
        seen = set()
        for name, setting, bad in failures:
            key = (name, tuple(sorted(bad.items())))
            if key in seen:
                continue
            seen.add(key)
            print(f"FAIL {name}: settings {setting}\n     mismatches (want, got): {bad}")
        print(f"blinded: {len(failures)} failing settings")
    return not failures
