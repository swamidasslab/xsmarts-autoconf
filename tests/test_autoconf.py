"""Autoconf self-tests. Run: ../.venv/bin/python -m pytest tests -q"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoconf.adapter import Case, canon  # noqa: E402
from autoconf.adapters import ADAPTERS, make  # noqa: E402
from autoconf.rules import load_rules, satisfies  # noqa: E402
from autoconf.run import CONFIG_DIR, autoconf, values  # noqa: E402

RULES = load_rules()


def _available(name: str) -> bool:
    try:
        return make(name).observe(Case("probe", "match", "C", "C")).text == "match:1"
    except Exception:  # noqa: BLE001
        return False


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
    from autoconf.gen import all_features

    known = all_features()
    for r in RULES:
        for conj in r.avoid:
            assert conj <= known, f"{r.flag}: unknown features {set(conj) - known}"


def test_satisfies_patterns():
    assert satisfies("*", "error")
    assert satisfies("match:+", "match:3") and not satisfies("match:+", "match:0")
    assert satisfies(["error", "match:1"], "match:1")
    assert satisfies("re:products:.*\\*.*", "products:*=C")


def test_canon_keeps_h_labels():
    assert canon("[C][C]") == "[C][C]"
    assert canon("C(C)O") == "CCO"


# ------------------------------------------------------------------ configs reproduce


def _committed():
    for p in sorted(CONFIG_DIR.glob("*/*.json")):
        yield p


@pytest.mark.parametrize("path", list(_committed()), ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_committed_config_reproduces(path):
    """Regression guard: the installed library still behaves as its committed
    config says. A version bump changes the file name, so a mismatch here
    means the same version changed behavior or a rule changed."""
    cfg = json.loads(path.read_text())
    name = cfg["adapter"]
    if name not in ADAPTERS or not _available(name):
        pytest.skip(f"{name} unavailable")
    ad = make(name, **cfg["options"])
    if ad.version() != cfg["version"]:
        pytest.skip(f"installed {ad.version()} != config {cfg['version']}")
    now = values(autoconf(ad))
    want = values(cfg)
    diff = {f: (want.get(f), now.get(f)) for f in now if want.get(f) != now.get(f)}
    assert not diff, f"behavior changed (config, now): {diff}"


# ------------------------------------------------------------------ key options


def test_rdkit_use_chirality_option_flips_flag():
    rule = [r for r in RULES if r.flag == "match.atom_chirality"]
    assert values(autoconf(make("rdkit"), rule))["match.atom_chirality"] == "ignored"
    assert values(autoconf(make("rdkit", use_chirality=True), rule))["match.atom_chirality"] == "enforced"


# ------------------------------------------------------------------ round trip


@pytest.mark.skipif(not _available("xenosmarts"), reason="xenosmarts not built")
def test_xenosmarts_round_trip_unblinded():
    from autoconf.roundtrip import unblinded

    assert unblinded(["xenosmarts"], verbose=False)


@pytest.mark.skipif(not _available("xenosmarts"), reason="xenosmarts not built")
def test_xenosmarts_round_trip_blinded():
    from autoconf.roundtrip import blinded

    assert blinded(8, ["xenosmarts"], verbose=False)


# ------------------------------------------------------------------ fuzzer


@pytest.mark.skipif(not (_available("rdkit") and _available("chematic")), reason="needs rdkit + chematic")
@pytest.mark.parametrize("flag", ["match.unspecified_isotope", "match.implicit_h_lowercase_h",
                                  "smirks.reactant_aromaticity"])
def test_fuzzer_rediscovers_wrong_flag(flag):
    """Key fuzzer property: claim chematic behaves like rdkit on ``flag`` and
    the fuzzer must find an example carrying that flag's features."""
    from autoconf.fuzz import flipcheck

    rows = []
    for seed in range(3):  # deterministic; any of three fixed seeds
        rows = flipcheck("rdkit", "chematic", max_examples=1500, flags=[flag], verbose=False, seed=seed)
        if rows and rows[0]["rediscovered"]:
            return
    pytest.fail(f"not rediscovered: {rows}")


@pytest.mark.parametrize("path", sorted((ROOT / "findings").rglob("*.json")), ids=lambda p: p.stem)
def test_findings_replay(path):
    """Recorded findings still reproduce on the recorded versions."""
    from autoconf.fuzz import _adapter, replay

    rec = json.loads(path.read_text())
    for label, ver in rec["versions"].items():
        name = label.split("[")[0]
        if not _available(name) or _adapter(name).version() != ver:
            pytest.skip(f"{label} {ver} not installed")
    assert replay(path) == rec["observed"]
