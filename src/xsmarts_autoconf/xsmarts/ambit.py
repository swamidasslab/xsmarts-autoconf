"""Ambit-compatible SMIRKS processor (Python reference; docs/xenosmarts/AMBIT.md).

``AmbitReaction.compile(smirks)`` follows Ambit's parse/validation (A1–A6)
and derives the same edit lists as ``SMIRKSReaction.generateTransformationData``.
``AmbitReaction.apply(mol)`` reproduces
``applyTransformationWithSingleCopyForEachPos`` with BioTransformer's flags:
one product per kept mapping (A8), the edit at that location (A12–A16) and
result processing (A20–A25). Stereo is ignored (policy); A26 aromaticity is
not needed when products are compared by InChIKey.

Rule numbers (A…) refer to AMBIT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .build import build_querymol
from .match import AMBIT, Matcher, Profile
from .mol import Atom, Bond, Mol
from .types import (
    AnyAtom, AromaticBond, Aromatic, Aliphatic, AtomAnd, AtomExpr, AtomicNumber, BondAnd,
    BondExpr, Charge, DoubleBond, DownBond, DownOrUnspec, Element, QuadrupleBond,
    QueryMol, SingleBond, SingleOrAromatic, TripleBond, UpBond, UpOrUnspec,
)

_SYMBOL = {1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F", 14: "Si", 15: "P", 16: "S", 17: "Cl",
           34: "Se", 35: "Br", 53: "I", 33: "As", 11: "Na", 19: "K", 3: "Li", 12: "Mg"}


class AmbitParseError(ValueError):
    pass


class AmbitApplyError(RuntimeError):
    """Ambit throws while applying (e.g. NullPointerException on a reactant
    with several components: its sequence covers only the component of query
    atom 0, AMBIT.md A8b). BioTransformer gets no products."""


# ----------------------------------------------------------- concreteness


@dataclass(frozen=True)
class ConcreteAtom:
    z: int
    charge: int
    aromatic: bool | None


def _analyze(e: AtomExpr) -> tuple[int | None, bool | None, int]:
    """(element, aromaticity, charge) a high-AND sub-expression pins (A5)."""
    if isinstance(e, Element):
        from .mol import atomic_number

        return atomic_number(e.symbol[0].upper() + e.symbol[1:]), e.aromatic, 0
    if isinstance(e, AtomicNumber):
        return e.n, None, 0
    if isinstance(e, Charge):
        return None, None, e.value
    if isinstance(e, Aromatic):
        return None, True, 0
    if isinstance(e, Aliphatic):
        return None, False, 0
    if isinstance(e, AtomAnd) and e.tight:
        z = arom = None
        charge = 0
        for p in e.parts:
            pz, pa, pc = _analyze(p)
            if pz is not None:
                if z is not None and z != pz:
                    return None, None, 0
                z = pz
            if pa is not None:
                arom = pa
            if pc:
                charge = pc
        return z, arom, charge
    return None, None, 0  # OR, NOT, recursive, counts: no element


def to_atom(e: AtomExpr) -> ConcreteAtom | None:
    """Ambit ``SmartsToChemObject.toAtom`` (A5)."""
    parts = e.parts if isinstance(e, AtomAnd) and not e.tight else (e,)
    z = arom = None
    charge = 0
    for p in parts:
        pz, pa, pc = _analyze(p)
        if pz is not None:
            if z is not None and z != pz:
                return None
            z = pz
        if pa is not None:
            if arom is not None and arom != pa:
                arom = None
            else:
                arom = pa
        if pc:
            charge = pc
    if z is None:
        return None
    return ConcreteAtom(z, charge, arom)


_ORDER_OF = {SingleBond: 1, DoubleBond: 2, TripleBond: 3, QuadrupleBond: 4,
             UpBond: 1, DownBond: 1, UpOrUnspec: 1, DownOrUnspec: 1, SingleOrAromatic: 1}

AROMATIC_ORDER = "aromatic"  # concrete bond with no order (Ambit AromaticQueryBond)


def to_bond(e: BondExpr):
    """Ambit ``toBond``: an order (1–4), AROMATIC_ORDER, or None (undefined)."""
    if type(e) in _ORDER_OF:
        return _ORDER_OF[type(e)]
    if isinstance(e, AromaticBond):
        return AROMATIC_ORDER
    if isinstance(e, BondAnd):
        orders = {_ORDER_OF[type(p)] for p in e.parts if type(p) in _ORDER_OF}
        return orders.pop() if len(orders) == 1 else None
    return None  # OR, NOT, ~, @: undefined


# ------------------------------------------------------------- compile


@dataclass
class AmbitReaction:
    smirks: str
    query: QueryMol
    reactant: list[int]
    product: list[int]
    rmap: dict[int, int]  # reactant query atom -> product query atom (mapped)
    new_atoms: list[int]  # product query atoms created (A12)
    charges: dict[int, int]  # reactant query atom -> charge to set (A13)
    deleted: list[int]  # unmapped reactant query atoms (A9/A13)
    bond_edits: list[tuple]  # (kind, a, b, order); a/b = ('r', i) | ('n', k)
    errors: list[str] = field(default_factory=list)
    """Ambit "parse errors" that do not stop the reaction (A6b): Ambit records
    them, skips that one bond edit, and BioTransformer applies the rest."""
    matcher: Matcher = field(repr=False, default=None)  # type: ignore[assignment]

    @classmethod
    def compile(cls, smirks: str, profile: Profile = AMBIT) -> AmbitReaction:
        if smirks.count(">") < 2:
            raise AmbitParseError("missing separators '>'")  # A1
        q = build_querymol(smirks, "xsmarts")
        reactant = [i for i, r in enumerate(q.atom_role) if r == "reactant"]
        product = [i for i, r in enumerate(q.atom_role) if r == "product"]
        rmaps = [q.atoms[i].mapno for i in reactant if q.atoms[i].mapno is not None]
        pmaps = [q.atoms[i].mapno for i in product if q.atoms[i].mapno is not None]
        errors = []
        for label, maps in (("Reactant", rmaps), ("Product", pmaps)):  # A3
            seen = set()
            for m in maps:
                if m in seen:
                    errors.append(f"{label} Map Index {m} is repeated!")
                seen.add(m)
        for m in rmaps:
            if m not in pmaps:
                errors.append(f"Reactant Map Index {m} is not valid product map index!")
        for m in pmaps:
            if m not in rmaps:
                errors.append(f"Product Map Index {m} is not valid reactant map index!")
        if errors:
            raise AmbitParseError("\n".join(errors))
        by_map = {q.atoms[i].mapno: i for i in product if q.atoms[i].mapno is not None}
        rmap = {i: by_map[q.atoms[i].mapno] for i in reactant if q.atoms[i].mapno is not None}
        for r, p in rmap.items():  # A4
            ra, pa = to_atom(q.atoms[r].expr), to_atom(q.atoms[p].expr)
            if (ra is None) != (pa is None) or (ra and pa and ra.z != pa.z):
                errors.append(f"Map {q.atoms[r].mapno} atom types are inconsistent!")
        new_atoms = [i for i in product if q.atoms[i].mapno is None]
        for i in new_atoms:
            if to_atom(q.atoms[i].expr) is None:
                errors.append("Unmapped product atom with undefined type!")
        if errors:
            raise AmbitParseError("\n".join(errors))

        charges = {}
        for r, p in rmap.items():  # A13
            ra, pa = to_atom(q.atoms[r].expr), to_atom(q.atoms[p].expr)
            pc = pa.charge if pa else None
            rc = ra.charge if ra else None
            if pc is None and (rc is None or rc == 0):
                continue
            if pc == 0 and (rc is None or rc == 0):
                continue
            charges[r] = pc if pc is not None else 0

        qb = {}
        for b in q.bonds:
            qb[(b.a, b.b)] = b
            qb[(b.b, b.a)] = b
        inv = {p: r for r, p in rmap.items()}
        edits: list[tuple] = []
        soft: list[str] = []
        for b in q.bonds:  # A14: reactant bonds between mapped atoms
            if b.a not in rmap or b.b not in rmap or q.atom_role[b.a] != "reactant":
                continue
            pb = qb.get((rmap[b.a], rmap[b.b]))
            if pb is None:
                edits.append(("delete", ("r", b.a), ("r", b.b), None))
                continue
            r0, p0 = to_bond(b.expr), to_bond(pb.expr)
            if r0 is None:
                if p0 is not None and p0 != AROMATIC_ORDER:
                    edits.append(("order", ("r", b.a), ("r", b.b), p0))
                continue
            if p0 is None:
                soft.append("A product bond with undefined order")  # A6b: skip this edit
                continue
            if p0 == AROMATIC_ORDER:
                continue
            if isinstance(b.expr, SingleOrAromatic):
                if not isinstance(pb.expr, SingleOrAromatic):
                    edits.append(("order", ("r", b.a), ("r", b.b), p0))
            elif r0 != p0:
                edits.append(("order", ("r", b.a), ("r", b.b), p0))
        for b in q.bonds:  # A15: product bonds that create bonds
            if q.atom_role[b.a] != "product":
                continue
            ends = []
            for x in (b.a, b.b):
                ends.append(("r", inv[x]) if x in inv else ("n", new_atoms.index(x)))
            both_mapped = ends[0][0] == "r" and ends[1][0] == "r"
            if both_mapped and (ends[0][1], ends[1][1]) in qb:
                continue  # handled by A14
            p0 = to_bond(b.expr)
            if p0 is None or p0 == AROMATIC_ORDER:
                soft.append("A product bond with undefined order")  # A6b: bond not created
                continue
            edits.append(("create", ends[0], ends[1], p0))
        deleted = [i for i in reactant if q.atoms[i].mapno is None]
        rx = cls(smirks, q, reactant, product, rmap, new_atoms, charges, deleted, edits, soft)
        rx.matcher = Matcher(q, profile, atoms=reactant)
        return rx

    # --------------------------------------------------------------- apply

    def mappings(self, mol: Mol) -> list[dict[int, int]]:
        """Ambit's mappings in Ambit's order, then its non-identical subset (A8).

        Non-identical keeps the *first* mapping per atom set, so which role
        assignment survives depends on enumeration order: we reproduce
        ``IsomorphismTester`` exactly (``_ambit_isomorphisms``).
        """
        kept, seen = [], set()
        for m in _ambit_isomorphisms(self.matcher, self.reactant, mol):
            if any(v is None for v in m.values()):
                raise AmbitApplyError("fragmented reactant: unmapped query atoms (Ambit NPE)")
            key = frozenset(m.values())
            if key not in seen:
                seen.add(key)
                kept.append(m)
        return kept

    def apply_at(self, mol: Mol, mapping: dict[int, int]) -> Mol:
        """A12–A16 then A20–A25 on a copy of ``mol``."""
        atoms = list(mol.atoms)
        new_idx = []
        for qi in self.new_atoms:  # A12
            c = to_atom(self.query.atoms[qi].expr)
            assert c is not None
            new_idx.append(len(atoms))
            atoms.append(Atom(_SYMBOL.get(c.z, "C"), c.charge, 0, bool(c.aromatic)))
        for qi, ch in self.charges.items():  # A13 charges
            t = mapping[qi]
            atoms[t] = replace(atoms[t], charge=ch)

        def target(end):
            kind, i = end
            return mapping[i] if kind == "r" else new_idx[i]

        bonds = {(min(b.a, b.b), max(b.a, b.b)): b.order for b in mol.bonds}
        for kind, a, b, order in self.bond_edits:  # A14/A15
            x, y = target(a), target(b)
            key = (min(x, y), max(x, y))
            if kind == "delete":
                bonds.pop(key, None)
            else:
                bonds[key] = order
        dead = {mapping[qi] for qi in self.deleted}  # A13 deletions
        keep = [i for i in range(len(atoms)) if i not in dead]
        renum = {old: new for new, old in enumerate(keep)}
        out_atoms = [atoms[i] for i in keep]
        out_bonds = [Bond(renum[a], renum[b], o) for (a, b), o in bonds.items()
                     if a in renum and b in renum]
        # A25b: existing atoms on a bond whose order the edit changed fail CDK
        # re-typing and become Ambit dummies (R, atomic number 0).
        changed = {target(e) for kind, a, b, _ in self.bond_edits if kind == "order" for e in (a, b)}
        dummies = frozenset(renum[i] for i in changed
                            if i < len(mol.atoms) and i in renum and not mol.atoms[i].aromatic)
        out = process_product(Mol(out_atoms, out_bonds))
        out.dummies = dummies
        return out

    def apply(self, mol: Mol) -> list[Mol]:
        return [self.apply_at(mol, m) for m in self.mappings(mol)]


# ------------------------------------- Ambit IsomorphismTester (A8 enumeration)


def _ambit_isomorphisms(matcher: Matcher, qatoms: list[int], mol: Mol):
    """Port of Ambit ``IsomorphismTester.getAllIsomorphismMappings``.

    Query = the reactant atoms in SMARTS order (Ambit atom numbers), bonds in
    query bond order; ``TopLayer`` neighbour lists follow bond order for query
    and target alike. The sequence starts at query atom 0; each element is a
    centre plus its not-yet-sequenced neighbours, or a ring-closing bond.
    Search is a LIFO stack of partial mappings seeded with target atoms in
    index order; result order is the order nodes complete.
    """
    q = matcher.query
    pos = {qa: k for k, qa in enumerate(qatoms)}
    n = len(qatoms)
    qb = []  # (a, b, pred) in query bond order, Ambit atom numbers
    for b in q.bonds:
        if b.a in pos and b.b in pos:
            qb.append((pos[b.a], pos[b.b], matcher.qbonds[(b.a, b.b)]))
    top: list[list[tuple[int, int]]] = [[] for _ in range(n)]  # (nbr, qbond idx)
    for k, (a, b, _) in enumerate(qb):
        top[a].append((b, k))
        top[b].append((a, k))
    apred = [matcher.apred[qa] for qa in qatoms]

    def amatch(k: int, t: int) -> bool:
        return apred[k](mol, t)

    if n == 1:
        for t in range(len(mol.atoms)):
            if amatch(0, t):
                yield {qatoms[0]: t}
        return

    # --- setQueryAtomSequence
    seq: list[tuple[int | None, list[int], list[int]]] = []  # (centre, atoms, qbond idx)
    sequenced = [0]
    seq_bonds: set[frozenset[int]] = set()
    first = (0, [a for a, _ in top[0]], [k for _, k in top[0]])
    for a, _ in top[0]:
        sequenced.append(a)
        seq_bonds.add(frozenset((0, a)))
    seq.append(first)
    stack = [first]
    while stack:
        cur = stack.pop()
        for atom in cur[1]:
            layer = top[atom]
            if len(layer) == 1:
                continue
            flags = [1 if nb in sequenced else 0 for nb, _ in layer]
            new_el = None
            if flags.count(0) > 0:
                new_el = (atom, [], [])
                seq.append(new_el)
                stack.append(new_el)
            for (nb, kb), fl in zip(layer, flags):
                if fl == 0:
                    new_el[1].append(nb)
                    new_el[2].append(kb)
                    seq_bonds.add(frozenset((atom, nb)))
                    sequenced.append(nb)
                else:
                    if cur[0] == nb:
                        continue
                    if frozenset((atom, nb)) in seq_bonds:
                        continue
                    seq_bonds.add(frozenset((atom, nb)))
                    seq.append((None, [atom, nb], [kb]))

    # --- executeSequence / expandNode / generateNodes
    def bond_ok(ta: int, tb: int, kb: int) -> bool:
        k = mol.bond_index.get((ta, tb))
        return k is not None and qb[kb][2](mol, k)

    results = []
    nstack: list[tuple[int, list[int | None]]] = []
    centre0 = seq[0][0]
    for t in range(len(mol.atoms)):
        if amatch(centre0, t):
            node: list[int | None] = [None] * n
            node[centre0] = t
            nstack.append((0, node))

    def finish(el_num: int, node):
        if el_num == len(seq):
            results.append(node)
        else:
            nstack.append((el_num, node))

    while nstack:
        el_num, node = nstack.pop()
        centre, atoms, bonds = seq[el_num]
        if centre is None:  # ring-closing bond
            ta, tb = node[atoms[0]], node[atoms[1]]
            if bond_ok(ta, tb, bonds[0]):
                finish(el_num + 1, node)
            continue
        tc = node[centre]
        used = set(x for x in node if x is not None)
        cands = [nb for nb, _ in mol.adj[tc] if nb not in used]
        if len(atoms) > len(cands):
            continue
        # generateNodes: choices in nested-loop order (1-3 atoms) or an
        # explicit LIFO of partial tuples (4+ atoms), as in Ambit.
        L = len(atoms)

        def ok(slot: int, ci: int) -> bool:
            t = cands[ci]
            return amatch(atoms[slot], t) and bond_ok(tc, t, bonds[slot])

        def emit(choice):
            new = list(node)
            for slot, ci in enumerate(choice):
                new[atoms[slot]] = cands[ci]
            finish(el_num + 1, new)

        if L <= 3:
            def rec(slot, chosen):
                if slot == L:
                    emit(chosen)
                    return
                for ci in range(len(cands)):
                    if ci not in chosen and ok(slot, ci):
                        rec(slot + 1, chosen + [ci])
            rec(0, [])
        else:
            st = [[ci] for ci in range(len(cands)) if ok(0, ci)]
            while st:
                t = st.pop()
                if len(t) == L:
                    emit(t)
                    continue
                for ci in range(len(cands)):
                    if ci not in t and ok(len(t), ci):
                        st.append(t + [ci])

    for node in results:
        yield {qatoms[k]: node[k] for k in range(n)}


# ------------------------------------------------- result processing (A20–A25)

# Allowed valences by (element, charge): CDK atom typing as the H adder sees it.
_VALENCES: dict[tuple[str, int], tuple[int, ...]] = {
    ("C", 0): (4,), ("C", 1): (3,), ("C", -1): (3,),
    ("N", 0): (3,), ("N", 1): (4,), ("N", -1): (2,),
    ("O", 0): (2,), ("O", 1): (3,), ("O", -1): (1,),
    ("S", 0): (2, 4, 6), ("S", 1): (3,), ("S", -1): (1,),
    ("Se", 0): (2, 4, 6), ("P", 0): (3, 5), ("P", 1): (4,),
    ("B", 0): (3,), ("B", -1): (4,),
    ("F", 0): (1,), ("Cl", 0): (1, 3, 5, 7), ("Br", 0): (1, 3, 5, 7), ("I", 0): (1, 3, 5, 7),
    ("H", 0): (1,), ("Si", 0): (4,), ("As", 0): (3, 5),
}


def process_product(mol: Mol) -> Mol:
    """Ambit ``processProduct`` with BioTransformer flags, minus aromaticity (A20–A25).

    Aromatic flags are cleared (A21; bonds keep their Kekulé orders), implicit H
    is cleared (A22) and refilled to the smallest allowed valence (A23–A24).
    An atom whose bonds exceed every allowed valence cannot be typed and gets
    no implicit H (A25).
    """
    bsum = [0] * len(mol.atoms)
    for b in mol.bonds:
        bsum[b.a] += b.order
        bsum[b.b] += b.order
    atoms = []
    for i, a in enumerate(mol.atoms):
        allowed = _VALENCES.get((a.symbol, a.charge), ())
        fill = next((v - bsum[i] for v in allowed if v >= bsum[i]), 0)
        atoms.append(Atom(a.symbol, a.charge, fill, False, a.isotope))
    bonds = [Bond(b.a, b.b, b.order, False, False) for b in mol.bonds]
    return Mol(atoms, bonds)
