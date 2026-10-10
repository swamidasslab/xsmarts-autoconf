"""Native COSMolKit adapter contracts; skip when the optional wheel is absent."""

import pytest

pytest.importorskip("cosmolkit")

from xsmarts_autoconf.adapter import Case
from xsmarts_autoconf.adapters import make
from xsmarts_autoconf.rules import load_rules
from xsmarts_autoconf.run import autoconf, values


@pytest.mark.parametrize("query,expected", [("C", "ok"), ("[$(C=O)]", "ok"), ("[", "error")])
def test_parse_acceptance(query, expected):
    assert make("cosmolkit").observe(Case("parse", "parse", query)).text == expected


@pytest.mark.parametrize("uniquify,expected", [(True, 1), (False, 2)])
def test_match_uniquify(uniquify, expected):
    assert make("cosmolkit", uniquify=uniquify).match("CC", "CC", False) == expected


@pytest.mark.parametrize("explicit_h,expected", [(False, 0), (True, 2)])
def test_match_explicit_h(explicit_h, expected):
    assert make("cosmolkit").match("[H]", "O", explicit_h) == expected


@pytest.mark.parametrize("use_chirality,expected", [(False, "ignored"), (True, "enforced")])
def test_chirality_option(use_chirality, expected):
    rules = load_rules(flags=["match.atom_chirality"])
    result = autoconf(make("cosmolkit", use_chirality=use_chirality), rules)
    assert values(result)["match.atom_chirality"] == expected


@pytest.mark.parametrize("smirks,smiles,expected", [
    ("[C:1][O:2]>>[C:1]=[O:2]", "CO", [["C=O"]]),
    ("[C:1].[O:2]>>[C:1][O:2]", "CO", [["COCO"]]),
    ("[C:1][O:2]>>[C:1].[O:2]", "CO", [["C", "O"]]),
    ("[N:1]>>[N:1]C", "CO", []),
])
def test_apply_outcomes_and_product_objects(smirks, smiles, expected):
    assert make("cosmolkit").apply(smirks, smiles, False) == expected


@pytest.mark.parametrize("explicit_h", [False, True])
@pytest.mark.parametrize("view,expected", [
    ("products", "products:C.O"),
    ("objects", "objects:C + O"),
    ("count", "outcomes:1"),
    ("sanitized", "products:C.O"),
])
def test_apply_observation_views(explicit_h, view, expected):
    case = Case("cleavage", "apply", "[C:1][O:2]>>[C:1].[O:2]", "CO",
                explicit_h=explicit_h, view=view)
    assert make("cosmolkit").observe(case).text == expected


@pytest.mark.parametrize("smiles,expected", [
    ("[H]OC", "CO"),
    ("[C][C]", "[C][C]"),
    ("C(C)(C)(C)(C)C", None),
    ("not-smiles", None),
    ("", ""),
])
def test_sanitize_preserves_native_chemistry(smiles, expected):
    assert make("cosmolkit").sanitize(smiles) == expected


def test_tweak_can_use_registered_adapter():
    pytest.importorskip("rdkit")
    from xsmarts_autoconf.tweak import probe

    result = probe("cosmolkit", "rdkit", max_examples=40, seed=0, verbose=False)
    assert result["families"] == ["rdkit"]
    assert result["tweaks_tried"] == 40
