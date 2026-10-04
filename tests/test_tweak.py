"""Grammar-consistent tweaks: every grammar alternative and every operation
can be produced in every dialect, and every tweak re-parses."""

import pytest
from hypothesis import HealthCheck, find, given, settings
from hypothesis import strategies as st

from xsmarts_autoconf.tweak import (ATOM_OPS, BOND_OPS, atom_alternatives, bond_alternatives, grammar,
                                    parses, primitive, tags_in, tweaks)

FAMILIES = ["rdkit", "chematic", "openbabel", "cdk", "xsmarts"]
# A base with a bracket atom (with a map), a bare atom, an explicit and an implicit bond.
BASE = "[#6;R:1]-[#8]C"
QUICK = settings(max_examples=60, database=None, deadline=None, suppress_health_check=list(HealthCheck))


def _find(strategy, cond=lambda t: True):
    return find(strategy, cond, settings=settings(max_examples=200, database=None, deadline=None,
                                                  suppress_health_check=list(HealthCheck)))


@pytest.mark.parametrize("family", FAMILIES)
def test_every_alternative_has_a_spelling_that_parses(family):
    alts = atom_alternatives(family)
    assert alts
    for alt in alts:
        p = _find(primitive(family, alt))
        assert grammar(family).parse(f"[C;{p}]", start="bracket_atom"), (family, alt, p)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("op", ATOM_OPS)
def test_every_atom_op_with_every_alternative(family, op):
    alts = atom_alternatives(family) if op not in ("negate",) else [None]
    for alt in alts:
        t = _find(tweaks(BASE, (family,), kind="atom", op=op, alt=alt))
        assert t.op == f"atom.{op}" and parses(t.query, family), (family, op, alt, t)
        assert t.query != BASE


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("op", BOND_OPS)
def test_every_bond_op_with_every_bond(family, op):
    alts = bond_alternatives() if op != "negate" else [None]
    for alt in alts:
        if op == "replace" and alt == "-":
            continue  # BASE's only explicit bond is "-": replacing it with itself is no tweak
        t = _find(tweaks(BASE, (family,), kind="bond", op=op, alt=alt))
        assert t.op == f"bond.{op}" and parses(t.query, family), (family, op, alt, t)


@pytest.mark.parametrize("family", FAMILIES)
@QUICK
@given(data=st.data())
def test_random_tweaks_reparse(family, data):
    base = data.draw(st.sampled_from([BASE, "c1ccccc1", "[CH3][OH]", "C=C-C#N", "[N+;H3]C(=O)[O-]",
                                      "[C:1][O:2]>>[C:1].[O:2]"]))
    t = data.draw(tweaks(base, (family,)))
    assert parses(t.query, family)
    # the reactant side changed; products untouched
    assert t.query.split(">>")[1:] == base.split(">>")[1:]


def test_tags_name_grammar_alternatives():
    assert tags_in("[C;r6;!R2]=,:[$(CO);X3]") == {
        "symbol:aliphatic", "ring_size:n", "ring_membership:n", "connectivity:n", "bond:double", "bond:aromatic"}
