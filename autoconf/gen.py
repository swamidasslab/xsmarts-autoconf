"""Feature-tagged example generators for the fuzzer.

Every vocabulary item carries feature tags. Rules declare ``fuzz.avoid``
features; the generator drops tagged items *at construction time*, so known
divergences are never built (not built-then-rejected). Items are ordered
simple -> exotic, so Hypothesis shrinks toward the plainest example.

Feature names (keep in sync with rules' ``fuzz.avoid``):
  prim.*   atom primitives        bond.*  bond primitives
  syntax.* pattern structure      mol.*   molecule corpus properties
  edit.*   SMIRKS edit recipes    cond.explicit_h / op.apply_implicit_h / view.*
"""

from __future__ import annotations

from hypothesis import strategies as st

from .adapter import Case

F = frozenset

# (text, features)
ATOMS = [
    ("C", F()), ("O", F()), ("N", F()), ("c", F()), ("n", F()), ("*", F()),
    ("[#6]", F()), ("[#7]", F()), ("[#8]", F()), ("[C,N]", F()), ("[!C]", F()), ("[a]", F()),
    ("[N+]", F({"prim.charge"})), ("[O-]", F({"prim.charge"})),
    ("[CH3]", F({"prim.hcount"})), ("[CH2]", F({"prim.hcount"})), ("[OH]", F({"prim.hcount"})),
    ("[NH2]", F({"prim.hcount"})),
    ("[CD1]", F({"prim.degree"})), ("[CD3]", F({"prim.degree"})),
    ("[CX4]", F({"prim.connectivity"})), ("[Cv4]", F({"prim.valence"})),
    ("[R]", F({"prim.ring_count_R"})), ("[R2]", F({"prim.ring_count_R"})), ("[R3]", F({"prim.ring_count_R"})),
    ("[r5]", F({"prim.ring_size_r"})), ("[r6]", F({"prim.ring_size_r"})), ("[x2]", F({"prim.ring_conn"})),
    ("[$(CO)]", F({"prim.recursive"})), ("[$(C=O)]", F({"prim.recursive"})),
    ("[C;$(C[$(O)])]", F({"prim.recursive", "prim.recursive_nested"})),
    ("[*,#7]", F({"prim.or_any"})), ("[*,#1]", F({"prim.or_any", "prim.h_atom"})),
    ("[#1]", F({"prim.h_atom"})), ("[H]", F({"prim.h_atom"})), ("[H+]", F({"prim.proton"})),
    ("[N++]", F({"prim.charge_plusplus"})), ("[Ch]", F({"prim.implicit_h"})), ("[Ch1]", F({"prim.implicit_h"})),
    ("[12C]", F({"prim.isotope"})), ("[13C]", F({"prim.isotope"})),
    ("[C@H]", F({"prim.chiral"})), ("[C@@H]", F({"prim.chiral"})),
    ("[C^3]", F({"prim.hybridization"})), ("[C^2]", F({"prim.hybridization"})),
    ("[Ck6]", F({"prim.ring_k"})), ("[Cz1]", F({"prim.z"})), ("[CZ1]", F({"prim.z"})),
    ("[CD{1-2}]", F({"prim.range"})), ("[#X]", F({"prim.hash_x"})), ("[Ci1]", F({"prim.insaturation"})),
    ("[G16]", F({"prim.group"})), ("[A]", F({"prim.aliphatic_A"})), ("[se]", F({"prim.aromatic_se"})),
]

BONDS = [
    ("", F()), (":", F()), ("~", F()), ("#", F()), ("-", F({"bond.explicit_single"})),
    ("=", F({"bond.explicit_double"})), ("@", F({"bond.ring"})), ("!@", F({"bond.ring"})),
    ("/", F({"bond.stereo"})), ("->", F({"bond.dative"})),
]

MOLS = [
    ("CC", F()), ("CCO", F()), ("COC", F()), ("CN(C)C", F()), ("CC(=O)O", F()), ("C=CC=O", F()),
    ("N#CC", F()), ("ClCCBr", F()), ("CC(C)(C)O", F()), ("OCCN", F()), ("C1CC1", F({"mol.ring"})),
    ("C1CCCCC1", F({"mol.ring"})), ("C1CCOC1", F({"mol.ring"})),
    ("c1ccccc1", F({"mol.aromatic"})), ("Cc1ccccc1", F({"mol.aromatic"})), ("c1ccncc1", F({"mol.aromatic"})),
    ("c1cc[nH]c1", F({"mol.aromatic"})), ("Oc1ccccc1", F({"mol.aromatic"})),
    ("CS(=O)(=O)O", F({"mol.hypervalent"})), ("OP(=O)(O)O", F({"mol.hypervalent"})),
    ("C1CCC2CCCC2C1", F({"mol.fused_ring"})), ("C1CCC2(C1)CCCCC2", F({"mol.fused_ring"})),
    ("c1ccc2ccccc2c1", F({"mol.aromatic", "mol.fused_ring"})),
    ("C12C3C4C1C5C2C3C45", F({"mol.cage", "mol.fused_ring"})),
    ("C1C2CC3CC1CC(C2)C3", F({"mol.cage", "mol.fused_ring"})),
    ("C[NH3+]", F({"mol.charged"})), ("CC(=O)[O-]", F({"mol.charged"})), ("C[N+](C)(C)C", F({"mol.charged"})),
    ("[13CH3]C", F({"mol.isotope"})), ("F/C=C/F", F({"mol.stereo"})), ("C[C@H](N)O", F({"mol.stereo"})),
    ("CCO.O", F({"mol.multi_component"})), ("[H+]", F({"mol.charged"})),
    ("O=C1C=COC=C1", F({"mol.aromatic_exocyclic"})), ("O=C1C=CC=CC=C1", F({"mol.aromatic_exocyclic"})),
]

# SMIRKS reactant atoms: (spelling with {m} for the map number, element-ish symbol, features)
RATOMS = [
    ("[C:{m}]", F()), ("[O:{m}]", F()), ("[N:{m}]", F()), ("[#6:{m}]", F()),
    ("[CH3:{m}]", F({"prim.hcount"})), ("[c:{m}]", F({"edit.aromatic"})), ("[cH:{m}]", F({"edit.aromatic", "prim.hcount"})),
    ("[N+:{m}]", F({"prim.charge", "mol.charged"})), ("[*:{m}]", F({"prim.star_mapped"})),
    ("[C;$(CO):{m}]", F({"prim.recursive"})), ("[C;$(C[$(O)]):{m}]", F({"prim.recursive", "prim.recursive_nested"})),
]


def _prod(a: str) -> str:
    """Product spelling of a reactant atom: strip query-only parts."""
    return {"[CH3:{m}]": "[C:{m}]", "[cH:{m}]": "[c:{m}]", "[C;$(CO):{m}]": "[C:{m}]",
            "[C;$(C[$(O)]):{m}]": "[C:{m}]", "[#6:{m}]": "[#6:{m}]"}.get(a, a)


def _charge(a: str, q: str) -> str:
    base = _prod(a).replace("+", "")
    return base.replace(":{m}]", f"{q}:{{m}}]")


# Edit recipes: (name, features, builder(r1, r2) -> smirks). r1/r2 are RATOM spellings.
EDITS = [
    ("identity", F({"edit.identity"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}"),
    ("bond_double", F({"edit.bond_order", "edit.bond_order_valence"}),
     lambda a, b: f"{a.format(m=1)}-{b.format(m=2)}>>{_prod(a).format(m=1)}={_prod(b).format(m=2)}"),
    ("bond_single", F({"edit.bond_order"}),
     lambda a, b: f"{a.format(m=1)}={b.format(m=2)}>>{_prod(a).format(m=1)}-{_prod(b).format(m=2)}"),
    ("charge_plus", F({"edit.charge_change"}), lambda a, b: f"{a.format(m=1)}>>{_charge(a, '+').format(m=1)}"),
    ("charge_minus", F({"edit.charge_change"}), lambda a, b: f"{a.format(m=1)}>>{_charge(a, '-').format(m=1)}"),
    ("charge_plus2", F({"edit.charge_high"}), lambda a, b: f"{a.format(m=1)}>>{_charge(a, '+2').format(m=1)}"),
    ("neutralize", F({"edit.neutralize", "mol.charged"}), lambda a, b: f"[N+:1]>>[N:1]"),
    ("add_atom", F({"edit.add_atom"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}C"),
    ("add_group", F({"edit.add_atom"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}C(=O)C"),
    ("cleave_leaving_group", F({"edit.disconnect", "edit.byproduct"}),
     lambda a, b: f"{a.format(m=1)}[O:2]>>{_prod(a).format(m=1)}.[O:2]"),
    ("cleave_to_aldehyde", F({"edit.disconnect", "edit.byproduct", "edit.new_double_bond"}),
     lambda a, b: f"{a.format(m=1)}[CH3:2]>>{_prod(a).format(m=1)}.[C:2]=O"),
    ("disconnect", F({"edit.disconnect"}),
     lambda a, b: f"{a.format(m=1)}{b.format(m=2)}>>{_prod(a).format(m=1)}.{_prod(b).format(m=2)}"),
    ("unmapped_neighbor", F({"edit.unmapped_reactant"}), lambda a, b: f"{a.format(m=1)}O>>{_prod(a).format(m=1)}"),
    ("delete_mapped", F({"edit.delete_mapped"}),
     lambda a, b: f"{a.format(m=1)}{b.format(m=2)}>>{_prod(a).format(m=1)}"),
    ("element_change", F({"edit.element_change"}), lambda a, b: "[C:1]>>[N:1]"),
    ("star_retype", F({"edit.star_retype"}), lambda a, b: f"{a.format(m=1)}>>[*:1]C"),
    ("product_only_map", F({"edit.product_only_map"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}[N:9]"),
    ("h_remove", F({"edit.h_atom"}), lambda a, b: f"{a.format(m=1)}[H]>>{_prod(a).format(m=1)}"),
    ("h_add", F({"edit.h_atom"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}[H]"),
    ("h_pin", F({"edit.h_pin"}), lambda a, b: "[C:1]>>[CH2:1]"),
    ("undefined_bond", F({"edit.undefined_bond"}),
     lambda a, b: f"{a.format(m=1)}-{b.format(m=2)}>>{_prod(a).format(m=1)}=,:{_prod(b).format(m=2)}"),
    ("fragmented", F({"edit.fragmented"}),
     lambda a, b: f"{a.format(m=1)}.{b.format(m=2)}>>{_prod(a).format(m=1)}{_prod(b).format(m=2)}"),
]

VIEWS = [("products", F()), ("count", F({"view.count"})), ("sanitized", F({"view.sanitized"})),
         ("objects", F({"view.objects"}))]


def _feats(item) -> frozenset:
    return next(x for x in item if isinstance(x, frozenset))


def _allowed(items, avoid):
    return [it for it in items if not (_feats(it) & avoid)]


def _blocked(feats, conj) -> bool:
    return any(c <= feats for c in conj)


def split_avoid(avoid) -> tuple[frozenset, tuple[frozenset, ...]]:
    """Conjunction list -> (single features to drop at construction,
    multi-feature conjunctions to filter after drawing)."""
    single = frozenset(next(iter(c)) for c in avoid if len(c) == 1)
    return single, tuple(c for c in avoid if len(c) > 1 and not (c & single))


def _pick(items):
    return st.sampled_from(items) if items else st.nothing()


def site_features(smirks: str, smiles: str, explicit_h: bool) -> set[str]:
    """Derived (not recipe) features: how the reactant template hits the
    molecule, computed once with RDKit as a neutral reference.

    ``sites.multiple``: more than one matched atom set (engines differ on
    per-site outcomes vs all-sites-in-place vs flattened).
    ``sites.ordered_multiple``: the same atom set matched in several orders
    (symmetric pattern; engines differ on ordered vs atom-set mappings)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import AllChem

    RDLogger.DisableLog("rdApp.*")
    try:
        rxn = AllChem.ReactionFromSmarts(smirks)
        m = Chem.MolFromSmiles(smiles)
        if explicit_h:
            m = Chem.AddHs(m)
        out = set()
        for t in rxn.GetReactants():
            uniq = len(m.GetSubstructMatches(t, uniquify=True, maxMatches=1000))
            ordered = len(m.GetSubstructMatches(t, uniquify=False, maxMatches=1000))
            if uniq > 1:
                out.add("sites.multiple")
            if ordered > uniq:
                out.add("sites.ordered_multiple")
        return out
    except Exception:  # noqa: BLE001
        return set()


@st.composite
def match_case(draw, avoid: frozenset, conj=()):
    atoms, bonds, mols = _allowed(ATOMS, avoid), _allowed(BONDS, avoid), _allowed(MOLS, avoid)
    n = draw(st.integers(1, 3))
    feats = set()
    parts = []
    for i in range(n):
        if i:
            b, bf = draw(_pick(bonds))
            parts.append(b)
            feats |= bf
        a, af = draw(_pick(atoms))
        parts.append(a)
        feats |= af
    query = "".join(parts)
    if n >= 2 and "syntax.dot" not in avoid and draw(st.booleans()):
        a, af = draw(_pick(atoms))
        query = f"{query}.{a}"
        feats |= af | {"syntax.dot"}
    mol, mf = draw(_pick(mols))
    xh = "cond.explicit_h" not in avoid and draw(st.booleans())
    feats |= mf | ({"cond.explicit_h"} if xh else set()) | {"op.match"}
    if _blocked(feats, conj):
        draw(st.nothing())
    return Case("fuzz", "match", query, mol, xh), frozenset(feats)


@st.composite
def apply_case(draw, avoid: frozenset, conj=()):
    edits, ratoms, mols, views = (_allowed(EDITS, avoid), _allowed(RATOMS, avoid),
                                  _allowed(MOLS, avoid), _allowed(VIEWS, avoid))
    name, ef, build = draw(_pick(edits))
    a, af = draw(_pick(ratoms))
    b, bf = draw(_pick(ratoms))
    mol, mf = draw(_pick(mols))
    view, vf = draw(_pick(views))
    can_implicit = "op.apply_implicit_h" not in avoid
    can_explicit = "cond.explicit_h" not in avoid
    if not (can_implicit or can_explicit):
        draw(st.nothing())
    xh = can_explicit and (not can_implicit or draw(st.booleans()))
    feats = set(ef | af | bf | mf | vf) | {"op.apply"}
    feats |= {"cond.explicit_h"} if xh else {"op.apply_implicit_h"}
    smirks = build(a, b)
    feats |= site_features(smirks, mol, xh)
    if feats & avoid or _blocked(feats, conj):
        draw(st.nothing())  # combined recipe hit an avoided feature / conjunction
    return Case("fuzz", "apply", smirks, mol, xh, view), frozenset(feats)


def example(avoid, ops=("match", "apply")):
    """Strategy of (Case, features) outside every avoid conjunction."""
    single, conj = split_avoid(avoid)
    strategies = []
    if "match" in ops and "op.match" not in single:
        strategies.append(match_case(single, conj))
    if "apply" in ops and "op.apply" not in single:
        strategies.append(apply_case(single, conj))
    return st.one_of(strategies) if strategies else st.nothing()


def all_features() -> frozenset:
    out = set()
    for items in (ATOMS, BONDS, MOLS, RATOMS, EDITS, VIEWS):
        for it in items:
            out |= _feats(it)
    return frozenset(out | {"cond.explicit_h", "op.apply_implicit_h", "op.match", "op.apply", "syntax.dot",
                            "sites.multiple", "sites.ordered_multiple"})
