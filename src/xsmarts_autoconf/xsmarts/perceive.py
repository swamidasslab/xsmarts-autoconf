"""Perception for the reference engine: SMILES -> Mol without CDK (M2).

Steps, each separate and replaceable:

1. ``parse_smiles``: what was written (``smiles.py``).
2. ``kekulize``: a Kekulé assignment for written-aromatic atoms. Atoms that
   still need a π bond (by valence) are matched over aromatic bonds
   (maximum matching with augmenting paths).
3. Implicit H: organic-subset atoms get the smallest default valence ≥ their
   bond-order sum; bracket atoms keep their written count.
4. ``relevant_cycles``: rings by policy (unique, order-independent; never
   SSSR).
5. Aromatic flags: **chematic** (``apply_aromaticity``, Hückel), by policy.
   It's a different model from CDK's ``ElectronDonation.cdk`` that
   BioTransformer matches against (AMBIT.md B0); the divergence is measured,
   not hidden.
6. Optional explicit-H expansion (Ambit mode matches on explicit-H graphs).
"""

from __future__ import annotations

from itertools import combinations

from .mol import Atom, Bond, Mol
from .smiles import SmilesMol, parse_smiles

_DEFAULT_VALENCE = {"B": (3,), "C": (4,), "N": (3, 5), "O": (2,), "P": (3, 5), "S": (2, 4, 6),
                    "F": (1,), "Cl": (1,), "Br": (1,), "I": (1,), "Se": (2, 4, 6), "As": (3, 5)}
_BOND_ORDER = {None: 1, "-": 1, "=": 2, "#": 3, "$": 4, ":": 1, "/": 1, "\\": 1, "~": 1, "->": 1, "<-": 1}


def _symbol(written: str) -> str:
    return written if written == "*" else written[0].upper() + written[1:]


def kekulize(sm: SmilesMol) -> list[int]:
    """Bond orders (one per SmilesMol bond) with aromatic bonds Kekulé-assigned.

    Raises ValueError if no assignment exists (e.g. a written-aromatic ring
    that cannot alternate)."""
    arom = [a.symbol[0].islower() and a.symbol != "*" for a in sm.atoms]
    orders, arom_bonds = [], []
    for k, b in enumerate(sm.bonds):
        sym = b.symbol if b.symbol is not None else b.close_symbol
        aromatic_bond = arom[b.a] and arom[b.b] and sym in (None, ":")
        orders.append(1 if aromatic_bond else _BOND_ORDER.get(sym, 1))
        if aromatic_bond:
            arom_bonds.append(k)
    used = [0] * len(sm.atoms)
    for k, b in enumerate(sm.bonds):
        used[b.a] += orders[k]
        used[b.b] += orders[k]

    def needs_pi(i: int) -> bool:
        a = sm.atoms[i]
        if not arom[i]:
            return False
        sym = _symbol(a.symbol)
        h = a.hcount if a.hcount is not None else 0
        val = used[i] + h
        targets = _DEFAULT_VALENCE.get(sym, (4,))
        charge = a.charge
        if sym in ("N", "P") and charge == 1:
            targets = (4,)
        elif sym in ("C",) and charge != 0:
            targets = (3,)
        elif sym in ("O", "S") and charge == 1:
            targets = (3,)
        elif sym == "N" and charge == -1:
            targets = (2,)
        if a.hcount is None:  # organic subset: implicit H can absorb, π if one short of lowest valence
            return val + 1 == targets[0]
        return any(val + 1 == t for t in targets)

    need = {i for i in range(len(sm.atoms)) if needs_pi(i)}
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in need}
    for k in arom_bonds:
        b = sm.bonds[k]
        if b.a in need and b.b in need:
            adj[b.a].append((b.b, k))
            adj[b.b].append((b.a, k))
    mate: dict[int, tuple[int, int]] = {}

    def augment(u: int, seen: set[int]) -> bool:
        for v, k in adj[u]:
            if v in seen:
                continue
            seen.add(v)
            if v not in mate or augment(mate[v][0], seen):
                mate[v] = (u, k)
                mate[u] = (v, k)
                return True
        return False

    for u in sorted(need, key=lambda i: len(adj[i])):
        if u not in mate:
            augment(u, {u})
    if len(mate) != len(need):
        raise ValueError("cannot kekulize")
    for u, (_, k) in mate.items():
        orders[k] = 2
    return orders


def relevant_cycles(n: int, edges: list[tuple[int, int]], max_size: int = 24) -> list[frozenset[int]]:
    """Relevant cycles: simple cycles not a GF(2) sum of strictly shorter cycles.

    Unique for a graph (the union of all minimum cycle bases), so the result
    does not depend on atom order, unlike SSSR. Simple-cycle enumeration is
    capped at ``max_size`` atoms, which is ample for drug-like molecules.
    """
    adj: list[list[int]] = [[] for _ in range(n)]
    eidx: dict[frozenset[int], int] = {}
    for k, (a, b) in enumerate(edges):
        adj[a].append(b)
        adj[b].append(a)
        eidx[frozenset((a, b))] = k
    cycles: set[tuple[int, ...]] = set()
    for start in range(n):  # cycles whose smallest atom is `start`
        stack = [(start, [start])]
        while stack:
            v, path = stack.pop()
            for w in adj[v]:
                if w == start and len(path) >= 3:
                    c = tuple(path)
                    if c[1] < c[-1]:
                        cycles.add(c)
                elif w > start and w not in path and len(path) < max_size:
                    stack.append((w, path + [w]))

    def edge_mask(c: tuple[int, ...]) -> int:
        m = 0
        for i in range(len(c)):
            m |= 1 << eidx[frozenset((c[i], c[(i + 1) % len(c)]))]
        return m

    by_len: dict[int, list[tuple[int, ...]]] = {}
    for c in cycles:
        by_len.setdefault(len(c), []).append(c)
    basis: dict[int, int] = {}  # GF(2) row-echelon: pivot bit -> row

    def reduce(m: int) -> int:
        while m:
            p = m.bit_length() - 1
            if p not in basis:
                return m
            m ^= basis[p]
        return 0

    out = []
    for L in sorted(by_len):
        group = by_len[L]
        relevant = [c for c in group if reduce(edge_mask(c))]
        out.extend(frozenset(c) for c in relevant)
        for c in group:  # all length-L cycles join the span before the next length
            r = reduce(edge_mask(c))
            if r:
                basis[r.bit_length() - 1] = r
    return out


def _chematic_aromatic(smiles: str, n_atoms: int):
    import chematic

    m = chematic.from_smiles(smiles.split()[0]).apply_aromaticity()
    atoms = [bool(a[3]) for a in m.atom_table]
    bonds = {frozenset((b[0], b[1])): bool(b[3]) for b in m.bond_table}
    if len(atoms) != n_atoms:
        raise ValueError("chematic atom count differs")
    return atoms, bonds


def mol_from_smiles(smiles: str, *, explicit_h: bool = False, aromaticity: str = "chematic") -> Mol:
    sm = parse_smiles(smiles)
    orders = kekulize(sm)
    n = len(sm.atoms)
    used = [0] * n
    for k, b in enumerate(sm.bonds):
        used[b.a] += orders[k]
        used[b.b] += orders[k]
    atoms = []
    for i, a in enumerate(sm.atoms):
        sym = _symbol(a.symbol)
        if a.hcount is not None:
            h = a.hcount
        else:
            h = next((v - used[i] for v in _DEFAULT_VALENCE.get(sym, ()) if v >= used[i]), 0)
        atoms.append(Atom(sym, a.charge, h, False, a.isotope))
    arom_atoms, arom_bonds = _chematic_aromatic(smiles, n) if aromaticity == "chematic" else ([False] * n, {})
    edges = [(b.a, b.b) for b in sm.bonds]
    rings = relevant_cycles(n, edges)
    ring_edges = {frozenset((r_list[i], r_list[(i + 1) % len(r_list)]))
                  for r in rings for r_list in [_ring_order(r, edges)] for i in range(len(r_list))}
    atoms = [Atom(a.symbol, a.charge, a.hcount, arom_atoms[i], a.isotope) for i, a in enumerate(atoms)]
    bonds = [Bond(b.a, b.b, orders[k], arom_bonds.get(frozenset((b.a, b.b)), False),
                  frozenset((b.a, b.b)) in ring_edges) for k, b in enumerate(sm.bonds)]
    if explicit_h:
        atoms, bonds = _expand_h(atoms, bonds)
    return Mol(atoms, bonds, rings=rings)


def _ring_order(ring: frozenset[int], edges: list[tuple[int, int]]) -> list[int]:
    """Atoms of a ring in cycle order."""
    nbrs = {i: [] for i in ring}
    for a, b in edges:
        if a in ring and b in ring:
            nbrs[a].append(b)
            nbrs[b].append(a)
    start = min(ring)
    order, prev = [start], None
    while len(order) < len(ring):
        cur = order[-1]
        nxt = next(x for x in nbrs[cur] if x != prev and x not in order)
        prev = cur
        order.append(nxt)
    return order


def _expand_h(atoms: list[Atom], bonds: list[Bond]):
    """Implicit H -> explicit H atoms, appended after the heavy atoms (CDK order)."""
    atoms = list(atoms)
    bonds = list(bonds)
    n = len(atoms)
    for i in range(n):
        a = atoms[i]
        for _ in range(a.hcount):
            atoms.append(Atom("H"))
            bonds.append(Bond(i, len(atoms) - 1, 1))
        atoms[i] = Atom(a.symbol, a.charge, 0, a.aromatic, a.isotope)
    return atoms, bonds


__all__ = ["kekulize", "relevant_cycles", "mol_from_smiles"]

_ = combinations  # (kept for future ring-family helpers)
