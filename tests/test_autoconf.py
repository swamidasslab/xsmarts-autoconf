"""xsmarts-autoconf self-tests. Every library-dependent test skips when that
library is not installed. Run: python -m pytest -q"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xsmarts_autoconf.adapter import canon  # noqa: E402
from xsmarts_autoconf.adapters import ADAPTERS, make  # noqa: E402
from xsmarts_autoconf.rules import DATA, load_rules, satisfies  # noqa: E402
from xsmarts_autoconf.run import CONFIG_DIR, autoconf, check, values  # noqa: E402

RULES = load_rules()


_AVAIL: dict[str, bool] = {}


def _available(name: str) -> bool:
    if name not in _AVAIL:
        _AVAIL[name] = make(name).available()[0]
    return _AVAIL[name]


def _need(*names):
    return pytest.mark.skipif(not all(_available(n) for n in names),
                              reason=f"needs {', '.join(names)}")


# ------------------------------------------------------------------ catalog


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.flag)
def test_rule_values_are_distinguishable(rule):
    """Every pair of values must differ on at least one pinned case."""
    vals = list(rule.values)
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            assert any(
                rule.expect[c.id].get(a, "*") != rule.expect[c.id].get(b, "*")
                and "*" not in (rule.expect[c.id].get(a, "*"), rule.expect[c.id].get(b, "*"))
                for c in rule.cases
            ), f"{rule.flag}: {a} and {b} have no distinguishing case"


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.flag)
def test_rule_has_provenance_and_fuzz_tags(rule):
    assert rule.provenance.get("discovered") or rule.provenance.get("refs")
    assert rule.avoid, f"{rule.flag}: no fuzz.avoid features"


def test_avoid_features_exist_in_generator():
    from xsmarts_autoconf.gen import all_features

    known = all_features()
    for r in RULES:
        for conj in r.avoid:
            assert conj <= known, f"{r.flag}: unknown features {set(conj) - known}"


def test_satisfies_patterns():
    assert satisfies("*", "error")
    assert satisfies("match:+", "match:3") and not satisfies("match:+", "match:0")
    assert satisfies(["error", "match:1"], "match:1")
    assert satisfies("re:products:.*\\*.*", "products:*=C")


@_need("rdkit")
def test_canon_keeps_h_labels():
    assert canon("[C][C]") == "[C][C]"
    assert canon("C(C)O") == "CCO"


# ------------------------------------------------------------------ configs reproduce


@pytest.mark.parametrize("name", list(ADAPTERS))
def test_installed_version_matches_config(name):
    """For whatever version of each library is installed: its checked-in
    config must exist, be current with the rules, and still reproduce.
    ``changed`` = same rule, different result (library behavior changed);
    ``stale``/``missing`` = run ``xsmarts-autoconf update`` and commit."""
    if not _available(name):
        pytest.skip(f"{name} not installed")
    r = check(make(name))
    assert r["status"] == "ok", (
        f"{name} {r['version']}: {r['status']} changed={r.get('changed')} "
        f"stale={len(r.get('stale', []))} -> run `xsmarts-autoconf update {name}`")


# ------------------------------------------------------------------ key options


@_need("rdkit")
def test_rdkit_use_chirality_option_flips_flag():
    rule = [r for r in RULES if r.flag == "match.atom_chirality"]
    assert values(autoconf(make("rdkit"), rule))["match.atom_chirality"] == "ignored"
    assert values(autoconf(make("rdkit", use_chirality=True), rule))["match.atom_chirality"] == "enforced"


# ------------------------------------------------------------------ round trip


@_need("xenosmarts")
def test_xenosmarts_round_trip_unblinded():
    from xsmarts_autoconf.roundtrip import unblinded

    assert unblinded(["xenosmarts"], verbose=False)


@_need("xenosmarts")
def test_xenosmarts_round_trip_blinded():
    from xsmarts_autoconf.roundtrip import blinded

    assert blinded(8, ["xenosmarts"], verbose=False)


# ------------------------------------------------------------------ fuzzer


@_need("rdkit", "chematic")
@pytest.mark.parametrize("flag", ["match.unspecified_isotope", "match.implicit_h_lowercase_h",
                                  "smirks.reactant_aromaticity"])
def test_fuzzer_rediscovers_wrong_flag(flag):
    """Key fuzzer property: claim chematic behaves like rdkit on ``flag`` and
    the fuzzer must find an example carrying that flag's features."""
    from xsmarts_autoconf.fuzz import flipcheck

    rows = []
    for seed in range(3):  # deterministic; any of three fixed seeds
        rows = flipcheck("rdkit", "chematic", max_examples=1500, flags=[flag], verbose=False, seed=seed)
        if rows and rows[0]["rediscovered"]:
            return
    pytest.fail(f"not rediscovered: {rows}")


@pytest.mark.parametrize("path", sorted((DATA / "findings").rglob("*.json")), ids=lambda p: p.stem)
def test_findings_replay(path):
    """Recorded findings still reproduce on the recorded versions."""
    from xsmarts_autoconf.fuzz import _adapter, replay

    rec = json.loads(path.read_text())
    for label, ver in rec["versions"].items():
        name = label.split("[")[0]
        if not _available(name) or _adapter(name).version() != ver:
            pytest.skip(f"{label} {ver} not installed")
    assert replay(path) == rec["observed"]
