"""Reference SMARTS matcher: canonical QueryMol over Mol (Python executable spec).

``Matcher(query, profile).matches(mol)`` yields every mapping (one target
atom index per query atom) in a deterministic order: query atoms are visited
depth-first from atom 0, candidates in ascending target index.

Semantics are a **profile** (data, not branches). ``CDK`` reads the facts CDK
SMARTS uses on an explicit-H graph, as BioTransformer prepares substrates:

- ``H`` = implicit H + explicit H neighbours; ``h`` = implicit H only
- ``D`` = explicit neighbours (H atoms included); ``X`` = D + implicit H
- ``v`` = bond-order sum + implicit H (Kekulé orders)
- ``R`` = relevant cycles containing the atom; ``r`` = member of a relevant
  cycle of that size; ``x`` = ring bonds at the atom. Policy: relevant
  cycles, never SSSR (order-dependent); divergence from SSSR engines is
  accepted.
- unwritten bond = single or aromatic; ``-``/``=`` exclude aromatic bonds

Stereo (``@``/``@@``, ``/``/``\\`` direction) is **ignored** in this first pass
and reported in ``Matcher.warnings``: policy is undecided.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from .mol import Mol, atomic_number
from .types import (
    Aliphatic, AliphaticHeteroNeighbors, AnyAtom, AnyBond, Aromatic, AromaticBond,
    AtomAnd, AtomExpr, AtomicNumber, AtomNot, AtomOr, BondAnd, BondExpr, BondNot, BondOr,
    Charge, Chirality, Connectivity, Count, DativeLeft, DativeRight, Degree, DoubleBond,
    DownBond, DownOrUnspec, Element, HeteroAny, HeteroNeighbors, Hybridization, ImplicitH,
    Insaturation, Isotope, NonHDegree, PeriodicGroup, QuadrupleBond, QueryMol, Recursive,
    RingBond, RingConnectivity, RingMembership, RingSize, RingSizeK, SingleBond,
    SingleOrAromatic, TotalH, TripleBond, UnboundHybridization, UpBond, UpOrUnspec, Valence,
)


@dataclass(frozen=True)
class Profile:
    name: str
    ring_size_any: bool = True
    """``r<n>``: member of any ring of size n vs the smallest ring is size n."""
    single_excludes_aromatic: bool = True
    double_excludes_aromatic: bool = True
    or_drops_any: bool = False
    """Reproduce the CDK SmartsPattern bug in BioTransformer's jar: a bare
    ``*`` inside a comma-OR is dropped, so ``[*,#1]`` behaves as ``[#1]``
    (AMBIT.md, G1). Only BioTransformer's *gate* runs through CDK; Ambit's
    own SMIRKS parser does not have the bug."""
    nested_recursive_true: bool = False
    """Reproduce Ambit's SMIRKS matcher: a recursive SMARTS nested *inside*
    another recursive SMARTS is never evaluated and counts as true
    (``$([$(X)])`` matches every atom; AMBIT.md A7b)."""


CDK = Profile("cdk")
CDK_GATE = Profile("cdk-gate", or_drops_any=True)
AMBIT = Profile("ambit", nested_recursive_true=True)


class UnsupportedQuery(ValueError):
    pass


def _count_ok(c: Count, x: int, *, default_min: int = 1) -> bool:
    if c.value is not None:
        return x == c.value
    if c.range is not None:
        lo, hi = c.range.min, c.range.max
        return (lo is None or x >= lo) and (hi is None or x <= hi)
    return x >= default_min  # bare letter: "at least one" / "in a ring"


AtomPred = Callable[[Mol, int], bool]
BondPred = Callable[[Mol, int], bool]


class Matcher:
    def __init__(self, query: QueryMol, profile: Profile = CDK, atoms: list[int] | None = None,
                 depth: int = 0):
        """``atoms``: query atom subset to match (e.g. the reactant role).
        ``depth``: recursive-SMARTS nesting level (0 = top-level pattern)."""
        self.query = query
        self.profile = profile
        self.depth = depth
        self.qatoms = list(range(len(query.atoms))) if atoms is None else list(atoms)
        self.warnings: list[str] = []
        self._recursive: dict[int, Matcher] = {}
        self._rec_memo: dict[tuple[int, int, int], bool] = {}
        self.apred = {i: self._atom(query.atoms[i].expr) for i in self.qatoms}
        sel = set(self.qatoms)
        self.qbonds: dict[tuple[int, int], BondPred] = {}
        for b in query.bonds:
            if b.a in sel and b.b in sel:
                p = self._bond(b.expr)
                self.qbonds[(b.a, b.b)] = p
                self.qbonds[(b.b, b.a)] = p
        self.order = self._search_order()
        self.need = self._element_needs()

    # ----- compile atom / bond expressions to predicates

    def _atom(self, e: AtomExpr) -> AtomPred:
        P = self.profile
        if isinstance(e, AtomNot):
            f = self._atom(e.expr)
            return lambda m, i: not f(m, i)
        if isinstance(e, AtomAnd):
            fs = [self._atom(p) for p in e.parts]
            return lambda m, i: all(f(m, i) for f in fs)
        if isinstance(e, AtomOr):
            parts = e.parts
            if P.or_drops_any and any(isinstance(p, AnyAtom) for p in parts):
                parts = tuple(p for p in parts if not isinstance(p, AnyAtom)) or parts
            fs = [self._atom(p) for p in parts]
            return lambda m, i: any(f(m, i) for f in fs)
        if isinstance(e, AnyAtom):
            return lambda m, i: True
        if isinstance(e, Element):
            sym = e.symbol[0].upper() + e.symbol[1:]
            if e.aromatic is None:
                return lambda m, i: m.atoms[i].symbol == sym
            return lambda m, i: m.atoms[i].symbol == sym and m.atoms[i].aromatic == e.aromatic
        if isinstance(e, AtomicNumber):
            return lambda m, i: m.atoms[i].z == e.n
        if isinstance(e, Aromatic):
            return lambda m, i: m.atoms[i].aromatic
        if isinstance(e, Aliphatic):
            return lambda m, i: not m.atoms[i].aromatic
        if isinstance(e, Charge):
            return lambda m, i: m.atoms[i].charge == e.value
        if isinstance(e, Isotope):
            return lambda m, i: m.atoms[i].isotope == e.mass
        if isinstance(e, TotalH):
            return lambda m, i: _count_ok(e.count, m.total_h(i))
        if isinstance(e, ImplicitH):
            return lambda m, i: _count_ok(e.count, m.atoms[i].hcount)
        if isinstance(e, Degree):
            return lambda m, i: _count_ok(e.count, m.degree(i))
        if isinstance(e, Connectivity):
            return lambda m, i: _count_ok(e.count, m.degree(i) + m.atoms[i].hcount)
        if isinstance(e, Valence):
            return lambda m, i: _count_ok(e.count, m.valence(i))
        if isinstance(e, RingMembership):
            return lambda m, i: _count_ok(e.count, m.ring_count[i])
        if isinstance(e, RingConnectivity):
            return lambda m, i: _count_ok(e.count, m.ring_bond_count[i])
        if isinstance(e, RingSize):
            c = e.count
            if c.value is None and c.range is None:
                return lambda m, i: m.ring_count[i] > 0
            if P.ring_size_any:
                return lambda m, i: any(_count_ok(c, s) for s in m.ring_sizes[i])
            return lambda m, i: bool(m.ring_sizes[i]) and _count_ok(c, min(m.ring_sizes[i]))
        if isinstance(e, RingSizeK):
            return lambda m, i: any(_count_ok(e.count, s) for s in m.ring_sizes[i]) if (
                e.count.value is not None or e.count.range is not None) else m.ring_count[i] > 0
        if isinstance(e, HeteroAny):
            return lambda m, i: m.atoms[i].z not in (1, 6)
        if isinstance(e, PeriodicGroup):
            return lambda m, i: m.group(i) == e.n
        if isinstance(e, HeteroNeighbors):
            return lambda m, i: _count_ok(e.count, sum(1 for n, _ in m.adj[i] if m.atoms[n].z not in (1, 6)))
        if isinstance(e, AliphaticHeteroNeighbors):
            return lambda m, i: _count_ok(e.count, sum(
                1 for n, _ in m.adj[i] if m.atoms[n].z not in (1, 6) and not m.atoms[n].aromatic))
        if isinstance(e, NonHDegree):
            return lambda m, i: _count_ok(e.count, m.heavy_degree(i))
        if isinstance(e, Insaturation):
            # CDK `i`: number of multiple-bond π contributions at the atom.
            return lambda m, i: _count_ok(e.count, sum(m.bonds[k].order - 1 for _, k in m.adj[i]))
        if isinstance(e, Recursive):
            if P.nested_recursive_true and self.depth >= 1:
                return lambda m, i: True
            sub = Matcher(e.mol, self.profile, depth=self.depth + 1)
            self.warnings.extend(sub.warnings)
            key = id(sub)
            self._recursive[key] = sub
            anchor = e.anchor

            def rec(m: Mol, i: int, sub=sub, key=key, anchor=anchor) -> bool:
                memo = (id(m), key, i)
                if memo not in self._rec_memo:
                    self._rec_memo[memo] = sub.exists(m, fixed={anchor: i})
                return self._rec_memo[memo]

            return rec
        if isinstance(e, Chirality):
            self.warnings.append("stereo: atom chirality ignored (policy undecided)")
            return lambda m, i: True
        if isinstance(e, (Hybridization, UnboundHybridization)):
            raise UnsupportedQuery("hybridization (^n) needs perceived hybridization; not in Mol yet")
        raise UnsupportedQuery(f"atom primitive {type(e).__name__}")

    def _bond(self, e: BondExpr) -> BondPred:
        P = self.profile
        if isinstance(e, BondNot):
            f = self._bond(e.expr)
            return lambda m, k: not f(m, k)
        if isinstance(e, BondAnd):
            fs = [self._bond(p) for p in e.parts]
            return lambda m, k: all(f(m, k) for f in fs)
        if isinstance(e, BondOr):
            fs = [self._bond(p) for p in e.parts]
            return lambda m, k: any(f(m, k) for f in fs)
        if isinstance(e, SingleOrAromatic):
            return lambda m, k: m.bonds[k].aromatic or m.bonds[k].order == 1
        if isinstance(e, (SingleBond, UpBond, DownBond, UpOrUnspec, DownOrUnspec)):
            if not isinstance(e, SingleBond):
                self.warnings.append("stereo: bond direction (/ \\) ignored (policy undecided)")
            if P.single_excludes_aromatic:
                return lambda m, k: m.bonds[k].order == 1 and not m.bonds[k].aromatic
            return lambda m, k: m.bonds[k].order == 1
        if isinstance(e, DoubleBond):
            if P.double_excludes_aromatic:
                return lambda m, k: m.bonds[k].order == 2 and not m.bonds[k].aromatic
            return lambda m, k: m.bonds[k].order == 2
        if isinstance(e, TripleBond):
            return lambda m, k: m.bonds[k].order == 3
        if isinstance(e, QuadrupleBond):
            return lambda m, k: m.bonds[k].order == 4
        if isinstance(e, AromaticBond):
            return lambda m, k: m.bonds[k].aromatic
        if isinstance(e, AnyBond):
            return lambda m, k: True
        if isinstance(e, RingBond):
            return lambda m, k: m.bonds[k].ring
        if isinstance(e, (DativeLeft, DativeRight)):
            raise UnsupportedQuery("dative bonds")
        raise UnsupportedQuery(f"bond primitive {type(e).__name__}")

    # ----- search plan

    def _search_order(self) -> list[tuple[int, int | None]]:
        """(query atom, already-placed query neighbour or None), DFS by component."""
        sel = set(self.qatoms)
        nbrs: dict[int, list[int]] = {i: [] for i in self.qatoms}
        for (a, b) in self.qbonds:
            nbrs[a].append(b)
        for v in nbrs.values():
            v.sort()
        seen: set[int] = set()
        order: list[tuple[int, int | None]] = []
        for root in self.qatoms:
            if root in seen:
                continue
            stack = [(root, None)]
            while stack:
                q, parent = stack.pop()
                if q in seen:
                    continue
                seen.add(q)
                order.append((q, parent))
                for n in reversed(nbrs[q]):
                    if n not in seen and n in sel:
                        stack.append((n, q))
        return order

    def _element_needs(self) -> dict[int, int]:
        """Lower bound on target element counts (from plain Element/#n atoms)."""
        need: dict[int, int] = {}
        for i in self.qatoms:
            z = _required_z(self.query.atoms[i].expr)
            if z:
                need[z] = need.get(z, 0) + 1
        return need

    # ----- matching

    def _prefilter(self, m: Mol) -> bool:
        ec = m.element_counts
        return all(ec.get(z, 0) >= n for z, n in self.need.items())

    def matches(self, m: Mol, fixed: dict[int, int] | None = None) -> Iterator[dict[int, int]]:
        """All mappings {query atom -> target atom}; deterministic order."""
        if not self._prefilter(m):
            return
        mapping: dict[int, int] = {}
        used: set[int] = set()
        order = self.order
        n = len(order)
        fixed = fixed or {}

        def candidates(depth: int):
            q, parent = order[depth]
            if q in fixed:
                return [fixed[q]]
            if parent is None:
                return range(len(m.atoms))
            return sorted(t for t, _ in m.adj[mapping[parent]])

        def ok(q: int, t: int) -> bool:
            if t in used or not self.apred[q](m, t):
                return False
            for (a, b), pred in self.qbonds.items():
                if a == q and b in mapping:
                    k = m.bond_index.get((t, mapping[b]))
                    if k is None or not pred(m, k):
                        return False
            return True

        def go(depth: int):
            if depth == n:
                yield dict(mapping)
                return
            q = order[depth][0]
            for t in candidates(depth):
                if ok(q, t):
                    mapping[q] = t
                    used.add(t)
                    yield from go(depth + 1)
                    del mapping[q]
                    used.discard(t)

        yield from go(0)

    def exists(self, m: Mol, fixed: dict[int, int] | None = None) -> bool:
        return next(self.matches(m, fixed), None) is not None


def _required_z(e: AtomExpr) -> int | None:
    if isinstance(e, Element):
        return atomic_number(e.symbol[0].upper() + e.symbol[1:])
    if isinstance(e, AtomicNumber):
        return e.n
    if isinstance(e, AtomAnd):
        for p in e.parts:
            z = _required_z(p)
            if z:
                return z
    return None
