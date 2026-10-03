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

from functools import lru_cache

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
    ("@-", F({"bond.compound", "bond.explicit_single", "bond.ring"})), ("-;@", F({"bond.compound", "bond.explicit_single", "bond.ring"})),
    ("=;@", F({"bond.compound", "bond.explicit_double", "bond.ring"})),
]

MOLS = [
    ("CC", F()), ("CCO", F()), ("COC", F()), ("CN(C)C", F()), ("CC(=O)O", F()), ("C=CC=O", F()),
    ("N#CC", F()), ("ClCCBr", F()), ("CC(C)(C)O", F()), ("OCCN", F()), ("C1CC1", F({"mol.ring"})),
    ("C1CCCCC1", F({"mol.ring"})), ("C1CCOC1", F({"mol.ring"})),
    ("c1ccccc1", F({"mol.aromatic"})), ("C1=CC=CC=C1", F({"mol.aromatic", "mol.kekule_aromatic"})), ("Cc1ccccc1", F({"mol.aromatic", "mol.aromatic_nonbenzene"})), ("c1ccncc1", F({"mol.aromatic", "mol.aromatic_nonbenzene"})),
    ("c1cc[nH]c1", F({"mol.aromatic", "mol.aromatic_nonbenzene"})), ("Oc1ccccc1", F({"mol.aromatic", "mol.aromatic_nonbenzene"})),
    ("CS(=O)(=O)O", F({"mol.hypervalent"})), ("OP(=O)(O)O", F({"mol.hypervalent"})),
    ("C1CCC2CCCC2C1", F({"mol.fused_ring"})), ("C1CCC2(C1)CCCCC2", F({"mol.fused_ring"})),
    ("c1ccc2ccccc2c1", F({"mol.aromatic", "mol.fused_ring", "mol.aromatic_nonbenzene"})),
    ("C12C3C4C1C5C2C3C45", F({"mol.cage", "mol.fused_ring"})),
    ("C1C2CC3CC1CC(C2)C3", F({"mol.cage", "mol.fused_ring"})),
    ("C[NH3+]", F({"mol.charged"})), ("CC(=O)[O-]", F({"mol.charged"})), ("C[N+](C)(C)C", F({"mol.charged"})),
    ("[13CH3]C", F({"mol.isotope"})), ("F/C=C/F", F({"mol.stereo"})), ("C[C@H](N)O", F({"mol.stereo"})),
    ("CCO.O", F({"mol.multi_component"})), ("[H+]", F({"mol.charged", "mol.proton"})),
    ("O=C1C=COC=C1", F({"mol.aromatic_exocyclic", "mol.aromatic", "mol.aromatic_nonbenzene"})), ("O=C1C=CC=CC=C1", F({"mol.aromatic_exocyclic", "mol.aromatic", "mol.aromatic_nonbenzene"})),
]

# SMIRKS reactant atoms: (spelling with {m} for the map number, element-ish symbol, features)
RATOMS = [
    ("[C:{m}]", F()), ("[O:{m}]", F()), ("[N:{m}]", F()), ("[#6:{m}]", F()),
    ("[CH3:{m}]", F({"prim.hcount"})), ("[c:{m}]", F({"edit.aromatic"})), ("[cH:{m}]", F({"edit.aromatic", "prim.hcount"})),
    ("[N+:{m}]", F({"prim.charge", "mol.charged"})), ("[*:{m}]", F({"prim.star_mapped"})),
    ("[C;$(CO):{m}]", F({"prim.recursive", "syntax.smirks_reactant_logic"})),
    ("[C;$(C[$(O)]):{m}]", F({"prim.recursive", "prim.recursive_nested", "syntax.smirks_reactant_logic"})),
]


_PROD: dict[str, str] = {}
"""Product spellings registered by the molecule-first generator."""


def _prod(a: str) -> str:
    """Product spelling of a reactant atom: strip query-only parts."""
    if a in _PROD:
        return _PROD[a]
    return {"[CH3:{m}]": "[C:{m}]", "[cH:{m}]": "[c:{m}]", "[C;$(CO):{m}]": "[C:{m}]",
            "[C;$(C[$(O)]):{m}]": "[C:{m}]", "[#6:{m}]": "[#6:{m}]"}.get(a, a)


def _charge(a: str, q: str) -> str:
    """Product spelling with charge ``q`` replacing any existing charge."""
    import re

    base = re.sub(r"[+-]\d*(?=:\{m\}\])", "", _prod(a))
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
    ("add_query_bond", F({"edit.add_atom", "edit.query_new_bond"}), lambda a, b: f"{a.format(m=1)}>>{_prod(a).format(m=1)}~C"),
    ("colon_product", F({"edit.colon_product"}),
     lambda a, b: f"{a.format(m=1)}-{b.format(m=2)}>>{_prod(a).format(m=1)}:{_prod(b).format(m=2)}"),
    ("hydroperoxide", F({"edit.add_atom", "edit.bt_invalid"}), lambda a, b: "[O:1][H]>>[O:1]O"),
    ("ketene", F({"edit.bond_order", "edit.bt_invalid"}), lambda a, b: "[C:1][C:2]=[O:3]>>[C:1]=[C:2]=[O:3]"),
    ("grouped_products", F({"edit.disconnect", "syntax.component_group"}),
     lambda a, b: f"{a.format(m=1)}{b.format(m=2)}>>({_prod(a).format(m=1)}.{_prod(b).format(m=2)})"),
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


def _for_op(avoid: frozenset, conj, op: str) -> frozenset:
    """Inside one op's generator, a conjunction ``{x, op}`` is just ``x``:
    resolve it before drawing instead of rejecting afterwards."""
    return avoid | {next(iter(c - {op})) for c in conj if op in c and len(c - {op}) == 1}


def split_avoid(avoid) -> tuple[frozenset, tuple[frozenset, ...]]:
    """Conjunction list -> (single features to drop at construction,
    multi-feature conjunctions to filter after drawing)."""
    single = frozenset(next(iter(c)) for c in avoid if len(c) == 1)
    return single, tuple(c for c in avoid if len(c) > 1 and not (c & single))


def _pick(items, focus=frozenset()):
    """Draw an item; with ``focus``, half the draws come from items carrying a
    focus feature (vocabulary where engines historically diverge)."""
    if not items:
        return st.nothing()
    hot = [it for it in items if _feats(it) & focus]
    if hot and len(hot) < len(items):
        return st.one_of(st.sampled_from(items), st.sampled_from(hot))
    return st.sampled_from(items)


@lru_cache(maxsize=100_000)
def _rdkit_hits(smarts: str, smiles: str, explicit_h: bool) -> bool:
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    q, m = Chem.MolFromSmarts(smarts), Chem.MolFromSmiles(smiles)
    if q is None or m is None:
        return False
    return (Chem.AddHs(m) if explicit_h else m).HasSubstructMatch(q)


def _pick_mol(mols, smarts: str, explicit_h: bool, focus):
    """Mostly molecules the query / reactant template actually hits (RDKit as
    a neutral reference), so examples exercise behavior instead of all
    engines agreeing on "no match"; sometimes any molecule."""
    hits = [m for m in mols if _rdkit_hits(smarts, m[0], explicit_h)]
    if not hits:
        return _pick(mols, focus)
    return st.one_of(_pick(hits, focus), _pick(hits, focus), _pick(mols, focus))


@lru_cache(maxsize=100_000)
def match_site_features(smarts: str, smiles: str, explicit_h: bool) -> frozenset[str]:
    """Derived features for a match query (RDKit reference): the same atom set
    matched in several orders (count semantics differ: atom sets vs mappings)."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    q, m = Chem.MolFromSmarts(smarts), Chem.MolFromSmiles(smiles)
    if q is None or m is None:
        return frozenset()
    if explicit_h:
        m = Chem.AddHs(m)
    uniq = len(m.GetSubstructMatches(q, uniquify=True, maxMatches=1000))
    ordered = len(m.GetSubstructMatches(q, uniquify=False, maxMatches=1000))
    return frozenset({"sites.ordered_multiple"} if ordered > uniq else set())


@lru_cache(maxsize=100_000)
def site_features(smirks: str, smiles: str, explicit_h: bool) -> frozenset[str]:
    """Derived (not recipe) features: how the reactant template hits the
    molecule, computed once with RDKit as a neutral reference.

    ``sites.multiple``: more than one matched atom set (engines differ on
    per-site outcomes vs all-sites-in-place vs flattened).
    ``sites.ordered_multiple``: the same atom set matched in several orders
    (symmetric pattern; engines differ on ordered vs atom-set mappings).
    ``edit.mapped_aromatic_nh``: a mapped atom lands on an aromatic N-H.
    ``outcome.valence_invalid``: some raw RDKit product fails SanitizeMol
    (engines differ on keep / drop / rewrite of invalid products)."""
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
            mapped = [a.GetIdx() for a in t.GetAtoms() if a.GetAtomMapNum()]
            for hit in m.GetSubstructMatches(t, maxMatches=50):
                for qi in mapped:
                    at = m.GetAtomWithIdx(hit[qi])
                    if at.GetAtomicNum() == 7 and at.GetIsAromatic() and at.GetTotalNumHs() > 0:
                        out.add("edit.mapped_aromatic_nh")
            uniq = len(m.GetSubstructMatches(t, uniquify=True, maxMatches=1000))
            ordered = len(m.GetSubstructMatches(t, uniquify=False, maxMatches=1000))
            if uniq > 1:
                out.add("sites.multiple")
            if ordered > uniq:
                out.add("sites.ordered_multiple")
        if rxn.GetNumReactantTemplates() == 1:
            for outcome in rxn.RunReactants((m,), 50):
                for p in outcome:
                    q = Chem.RWMol(p)
                    for bd in q.GetBonds():  # query-order bonds (~, =,:) count as single
                        if bd.GetBondType() not in (Chem.BondType.SINGLE, Chem.BondType.DOUBLE,
                                                    Chem.BondType.TRIPLE, Chem.BondType.AROMATIC):
                            bd.SetBondType(Chem.BondType.SINGLE)
                    try:
                        Chem.SanitizeMol(q)
                    except Exception:  # noqa: BLE001
                        out.add("outcome.valence_invalid")
        return frozenset(out)
    except Exception:  # noqa: BLE001
        return frozenset()


@st.composite
def match_case(draw, avoid: frozenset, conj=(), focus=frozenset()):
    avoid = _for_op(avoid, conj, "op.match")
    atoms, bonds, mols = _allowed(ATOMS, avoid), _allowed(BONDS, avoid), _allowed(MOLS, avoid)
    n = draw(st.integers(1, 3))
    feats = set()
    parts = []
    for i in range(n):
        if i:
            b, bf = draw(_pick(bonds, focus))
            parts.append(b)
            feats |= bf
        a, af = draw(_pick(atoms, focus))
        parts.append(a)
        feats |= af
    query = "".join(parts)
    if n >= 2 and "syntax.dot" not in avoid and draw(st.booleans()):
        a, af = draw(_pick(atoms, focus))
        if "syntax.component_group" not in avoid and draw(st.booleans()):
            query = f"({query}).({a})"
            feats |= {"syntax.component_group"}
        else:
            query = f"{query}.{a}"
        feats |= af | {"syntax.dot"}
    elif n >= 2 and "syntax.unclosed_ring" not in avoid and draw(st.integers(0, 9)) == 0:
        query = query[:1] + "1" + query[1:] if query[0].isalpha() and query[0] != "[" else query + "1"
        feats |= {"syntax.unclosed_ring"}
    xh = "cond.explicit_h" not in avoid and draw(st.booleans())
    mol, mf = draw(_pick_mol(mols, query, xh, focus))
    feats |= mf | ({"cond.explicit_h"} if xh else set()) | {"op.match"}
    feats |= match_site_features(query, mol, xh)
    if _blocked(feats, conj):
        draw(st.nothing())
    return Case("fuzz", "match", query, mol, xh), frozenset(feats)


@st.composite
def apply_case(draw, avoid: frozenset, conj=(), focus=frozenset()):
    avoid = _for_op(avoid, conj, "op.apply")
    edits, ratoms, mols, views = (_allowed(EDITS, avoid), _allowed(RATOMS, avoid),
                                  _allowed(MOLS, avoid), _allowed(VIEWS, avoid))
    name, ef, build = draw(_pick(edits, focus))
    a, af = draw(_pick(ratoms, focus))
    b, bf = draw(_pick(ratoms, focus))
    view, vf = draw(_pick(views, focus))
    can_implicit = "op.apply_implicit_h" not in avoid
    can_explicit = "cond.explicit_h" not in avoid
    if not (can_implicit or can_explicit):
        draw(st.nothing())
    xh = can_explicit and (not can_implicit or draw(st.booleans()))
    smirks = build(a, b)
    mol, mf = draw(_pick_mol(mols, smirks.split(">")[0], xh, focus))
    feats = set(ef | af | bf | mf | vf) | {"op.apply"}
    feats |= {"cond.explicit_h"} if xh else {"op.apply_implicit_h"}
    feats |= site_features(smirks, mol, xh)
    if feats & avoid or _blocked(feats, conj):
        draw(st.nothing())  # combined recipe hit an avoided feature / conjunction
    return Case("fuzz", "apply", smirks, mol, xh, view), frozenset(feats)


# ------------------------------------------------------------ molecule-first

def _atom_primitives(atom) -> list[tuple[str, frozenset]]:
    """Primitives that are true for this RDKit atom, each feature-tagged.
    RDKit's perception is the neutral reference; engines that perceive the
    molecule differently show up as findings."""
    sym = atom.GetSymbol()
    elem = sym.lower() if atom.GetIsAromatic() else sym
    ri = atom.GetOwningMol().GetRingInfo()
    nrings = ri.NumAtomRings(atom.GetIdx())
    out = [(f"#{atom.GetAtomicNum()}", F()), ("a" if atom.GetIsAromatic() else "A", F({"prim.aliphatic_A"} if not atom.GetIsAromatic() else set())),
           (f"H{atom.GetTotalNumHs()}", F({"prim.hcount"})), (f"D{atom.GetDegree()}", F({"prim.degree"})),
           (f"X{atom.GetTotalDegree()}", F({"prim.connectivity"})), (f"v{atom.GetTotalValence()}", F({"prim.valence"})),
           (f"h{atom.GetTotalNumHs()}", F({"prim.implicit_h"})), (f"R{nrings}", F({"prim.ring_count_R"}))]
    if nrings:
        smallest = min(len(r) for r in ri.AtomRings() if atom.GetIdx() in r)
        out.append((f"r{smallest}", F({"prim.ring_size_r"})))
        out.append((f"x{sum(1 for b in atom.GetBonds() if b.IsInRing())}", F({"prim.ring_conn"})))
    if atom.GetFormalCharge():
        c = atom.GetFormalCharge()
        out.append((("+" if c > 0 else "-") + (str(abs(c)) if abs(c) > 1 else ""), F({"prim.charge"})))
    nbrs = sorted({n.GetSymbol() for n in atom.GetNeighbors() if n.GetAtomicNum() > 1})
    if nbrs:
        out.append((f"$(*~[{nbrs[0]}])", F({"prim.recursive"})))
    if atom.GetIsotope():
        out.append((str(atom.GetIsotope()), F({"prim.isotope"})))
    if atom.GetAtomicNum() == 1:
        # every primitive on an H atom is an H-atom query: tag them all
        tag = F({"prim.h_atom", "prim.proton"} if atom.GetFormalCharge() else {"prim.h_atom"})
        return [(p, f | tag) for p, f in [(elem, F())] + out]
    return [(elem, F())] + out


def _bond_spelling(bond) -> tuple[str, frozenset]:
    from rdkit import Chem

    if bond.GetIsAromatic():
        return ":", F()
    t = bond.GetBondType()
    if t == Chem.BondType.DOUBLE:
        return "=", F({"bond.explicit_double"})
    if t == Chem.BondType.TRIPLE:
        return "#", F()
    return "-", F({"bond.explicit_single"})


@lru_cache(maxsize=1000)
def _rdmol(smiles: str, explicit_h: bool):
    from rdkit import Chem

    m = Chem.MolFromSmiles(smiles)
    return Chem.AddHs(m) if explicit_h else m


@st.composite
def mol_first_case(draw, avoid: frozenset, conj=(), focus=frozenset()):
    """Draw a molecule, then a 1-2 atom path in it, then a query whose atoms
    are built from primitives true for those atoms; optionally turn it into a
    SMIRKS by mapping the atoms and applying a tagged edit recipe."""
    op = draw(st.sampled_from(["match", "apply"]))
    avoid = _for_op(avoid, conj, f"op.{op}")
    mols = _allowed(MOLS, avoid)
    mol, mf = draw(_pick(mols, focus))
    if "." in mol:
        draw(st.nothing())
    m = _rdmol(mol, False)
    i = draw(st.integers(0, m.GetNumAtoms() - 1))
    path = [m.GetAtomWithIdx(i)]
    if draw(st.booleans()) and path[0].GetDegree():
        nb = draw(st.sampled_from(sorted(n.GetIdx() for n in path[0].GetNeighbors())))
        path.append(m.GetAtomWithIdx(nb))
    feats = set(mf) | {f"op.{op}", "gen.mol_first"}
    specs = []
    for at in path:
        prims = _allowed(_atom_primitives(at), avoid)
        if not prims:
            draw(st.nothing())
        k = draw(st.integers(1, min(3, len(prims))))
        chosen = [prims[0]] + draw(st.lists(st.sampled_from(prims[1:] or prims[:1]), min_size=k - 1, max_size=k - 1, unique=True))
        for _, f in chosen:
            feats |= f
        specs.append((";".join(dict.fromkeys(p for p, _ in chosen)), at))
    bond = ""
    if len(path) == 2:
        bond, bf = _bond_spelling(m.GetBondBetweenAtoms(path[0].GetIdx(), path[1].GetIdx()))
        if bf & avoid:
            bond, bf = "~", F()
        feats |= bf
    if op == "match":
        query = bond.join(f"[{e}]" for e, _ in specs)
        xh = "cond.explicit_h" not in avoid and draw(st.booleans())
        feats |= {"cond.explicit_h"} if xh else set()
        feats |= match_site_features(query, mol, xh)
        if _blocked(feats, conj):
            draw(st.nothing())
        return Case("fuzz", "match", query, mol, xh), frozenset(feats)
    ratoms = []
    for e, at in specs:
        sym = at.GetSymbol().lower() if at.GetIsAromatic() else at.GetSymbol()
        c = at.GetFormalCharge()
        chg = ("+" if c > 0 else "-") + (str(abs(c)) if abs(c) > 1 else "") if c else ""
        r = f"[{e}:{{m}}]"
        _PROD[r] = f"[{sym}{chg}:{{m}}]"
        ratoms.append(r)
    if any(";" in e for e, _ in specs):
        feats.add("syntax.smirks_reactant_logic")
    two = len(ratoms) == 2
    edits = [e for e in _allowed(EDITS, avoid) if two == ("{m}" in e[2]("A{m}", "B{m}").split(">")[0].replace("A{m}", "", 1))]
    name, ef, build = draw(_pick(edits, focus))
    smirks = build(ratoms[0], ratoms[-1])
    if two and bond not in ("", "-"):
        smirks = smirks.replace(ratoms[0].format(m=1) + ratoms[1].format(m=2),
                                ratoms[0].format(m=1) + bond + ratoms[1].format(m=2), 1)
    view, vf = draw(_pick(_allowed(VIEWS, avoid), focus))
    can_implicit = "op.apply_implicit_h" not in avoid
    can_explicit = "cond.explicit_h" not in avoid
    if not (can_implicit or can_explicit):
        draw(st.nothing())
    xh = can_explicit and (not can_implicit or draw(st.booleans()))
    feats |= set(ef | vf) | ({"cond.explicit_h"} if xh else {"op.apply_implicit_h"})
    feats |= site_features(smirks, mol, xh)
    if feats & avoid or _blocked(feats, conj):
        draw(st.nothing())
    return Case("fuzz", "apply", smirks, mol, xh, view), frozenset(feats)


def example(avoid, ops=("match", "apply"), focus=frozenset()):
    """Strategy of (Case, features) outside every avoid conjunction, biased
    toward ``focus`` features."""
    single, conj = split_avoid(avoid)
    strategies = []
    if "match" in ops and "op.match" not in single:
        strategies.append(match_case(single, conj, focus))
    if "apply" in ops and "op.apply" not in single:
        strategies.append(apply_case(single, conj, focus))
    if "mol_first" in ops or ops == ("match", "apply"):
        strategies.append(mol_first_case(single, conj, focus))
    return st.one_of(strategies) if strategies else st.nothing()


def all_features() -> frozenset:
    out = set()
    for items in (ATOMS, BONDS, MOLS, RATOMS, EDITS, VIEWS):
        for it in items:
            out |= _feats(it)
    return frozenset(out | {"cond.explicit_h", "op.apply_implicit_h", "op.match", "op.apply", "syntax.dot",
                            "sites.multiple", "sites.ordered_multiple", "outcome.valence_invalid",
                            "syntax.smirks_reactant_logic", "syntax.component_group", "syntax.unclosed_ring",
                            "edit.mapped_aromatic_nh",
                            "gen.mol_first"})
