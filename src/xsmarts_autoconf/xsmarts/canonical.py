"""Canonicalize QueryMol constraint trees so one meaning ↔ one IR shape."""

from __future__ import annotations

from .insat_patterns import fold_insaturation_patterns
from .types import (
    AnyAtom,
    AtomAnd,
    AtomExpr,
    AtomMap,
    AtomNot,
    AtomOr,
    BondAnd,
    BondExpr,
    BondNot,
    BondOr,
    Count,
    Insaturation,
    OpenRing,
    QueryAtom,
    QueryBond,
    QueryMol,
    Recursive,
)


def _atom_key(expr: AtomExpr) -> str:
    return repr(expr)


def _bond_key(expr: BondExpr) -> str:
    return repr(expr)


def _dedupe_sorted(parts: list) -> list:
    """Drop consecutive duplicates from a key-sorted list (And/Or idempotent)."""
    out: list = []
    for p in parts:
        if not out or out[-1] != p:
            out.append(p)
    return out


def _pull_atom_maps(expr: AtomExpr) -> tuple[AtomExpr | None, list[AtomMap]]:
    """Split atom-map primitives out of an expression (toolkit mapno is atom-level)."""
    if isinstance(expr, AtomMap):
        return None, [expr]
    if isinstance(expr, AtomNot):
        core, maps = _pull_atom_maps(expr.expr)
        if core is None:
            # ``!:1`` is meaningless as a lone map; keep as-is.
            return expr, []
        return AtomNot(core), maps
    if isinstance(expr, AtomAnd):
        cores: list[AtomExpr] = []
        maps: list[AtomMap] = []
        for p in expr.parts:
            c, m = _pull_atom_maps(p)
            if c is not None:
                cores.append(c)
            maps.extend(m)
        if not cores:
            return None, maps
        if len(cores) == 1:
            return cores[0], maps
        return AtomAnd(tuple(cores), tight=expr.tight), maps
    if isinstance(expr, AtomOr):
        cores_or: list[AtomExpr] = []
        maps_or: list[AtomMap] = []
        for p in expr.parts:
            c, m = _pull_atom_maps(p)
            if c is None:
                # Map-only OR arm — drop arm, keep map (``[C,:1]`` oddities).
                maps_or.extend(m)
                continue
            cores_or.append(c)
            maps_or.extend(m)
        if not cores_or:
            return None, maps_or
        if len(cores_or) == 1:
            return cores_or[0], maps_or
        return AtomOr(tuple(cores_or)), maps_or
    return expr, []


def canonicalize_atom_expr(expr: AtomExpr) -> AtomExpr:
    """Flatten logic, unwrap singletons, sort commutative AND/OR children.

    Atom maps are *not* match constraints: any ``AtomMap`` leaves are dropped.
    Callers that need ``:n`` must hoist via :func:`hoist_mapno` /
    :func:`canonicalize_querymol` onto :attr:`QueryAtom.mapno` first.
    """
    # CDK ``i0`` ≡ bare ``i`` (unsaturated), not exact-zero.
    if isinstance(expr, Insaturation) and expr.count.value == 0 and not expr.count.defaulted:
        expr = Insaturation(Count(defaulted=True))

    if isinstance(expr, AtomNot):
        inner = canonicalize_atom_expr(expr.expr)
        # ``!:1`` with nothing left — treat as ``!*`` (never matches).
        return AtomNot(inner)
    if isinstance(expr, AtomAnd):
        flat: list[AtomExpr] = []

        def absorb(c: AtomExpr) -> None:
            if isinstance(c, AtomMap):
                return
            if isinstance(c, AtomAnd):
                for q in c.parts:
                    absorb(q)
                return
            core, _maps = _pull_atom_maps(c)
            if core is not None:
                flat.append(core)

        for p in expr.parts:
            absorb(canonicalize_atom_expr(p))
        flat.sort(key=_atom_key)
        # And(C,C) ≡ C; chematic ``++`` = And(+1,+1) ≡ Charge(+1).
        flat = _dedupe_sorted(flat)
        if not flat:
            return AnyAtom()
        if len(flat) == 1:
            out: AtomExpr = flat[0]
        else:
            # ``;`` vs ``&`` only matter with OR among siblings.
            tight = not any(isinstance(p, AtomOr) for p in flat)
            out = AtomAnd(tuple(flat), tight=tight)
        folded = fold_insaturation_patterns(out)
        return folded if folded is not None else out
    if isinstance(expr, AtomOr):
        flat_or: list[AtomExpr] = []
        for p in expr.parts:
            c = canonicalize_atom_expr(p)
            core, _nested = _pull_atom_maps(c)
            if core is None:
                continue
            if isinstance(core, AtomOr):
                flat_or.extend(core.parts)
            else:
                flat_or.append(core)
        flat_or.sort(key=_atom_key)
        flat_or = _dedupe_sorted(flat_or)
        if not flat_or:
            return AnyAtom()
        if len(flat_or) == 1:
            out = flat_or[0]
        else:
            out = AtomOr(tuple(flat_or))
        folded = fold_insaturation_patterns(out)
        return folded if folded is not None else out
    if isinstance(expr, Recursive):
        rec = Recursive(
            mol=canonicalize_querymol(expr.mol),
            anchor=expr.anchor,
        )
        folded = fold_insaturation_patterns(rec)
        return folded if folded is not None else rec
    if isinstance(expr, AtomMap):
        # Preserve until :func:`hoist_mapno` (map-only → AnyAtom + mapno there).
        return expr
    return expr


def canonicalize_bond_expr(expr: BondExpr) -> BondExpr:
    if isinstance(expr, BondNot):
        return BondNot(canonicalize_bond_expr(expr.expr))
    if isinstance(expr, BondAnd):
        flat: list[BondExpr] = []

        def absorb(c: BondExpr) -> None:
            if isinstance(c, BondAnd):
                for q in c.parts:
                    absorb(q)
            else:
                flat.append(c)

        for p in expr.parts:
            absorb(canonicalize_bond_expr(p))
        flat.sort(key=_bond_key)
        if len(flat) == 1:
            return flat[0]
        tight = not any(isinstance(p, BondOr) for p in flat)
        return BondAnd(tuple(flat), tight=tight)
    if isinstance(expr, BondOr):
        flat_or: list[BondExpr] = []
        for p in expr.parts:
            c = canonicalize_bond_expr(p)
            if isinstance(c, BondOr):
                flat_or.extend(c.parts)
            else:
                flat_or.append(c)
        flat_or.sort(key=_bond_key)
        if len(flat_or) == 1:
            return flat_or[0]
        return BondOr(tuple(flat_or))
    return expr


def hoist_mapno(
    expr: AtomExpr, existing: int | None = None
) -> tuple[AtomExpr, int | None]:
    """Pull ``AtomMap`` out of ``expr`` → ``(match_expr, mapno)``.

    Map numbers are not match constraints. Pull *before* canonicalizing so
    ``:n`` is not lost when maps are stripped from the expression tree.
    """
    core, maps = _pull_atom_maps(expr)
    if existing is not None:
        mapno = existing
    elif maps:
        mapno = sorted({m.n for m in maps})[0]
    else:
        mapno = None
    if core is None:
        # ``[:1]`` / map-only → wildcard atom with mapno.
        core = AnyAtom()
    else:
        core = canonicalize_atom_expr(core)
    return core, mapno


def canonicalize_querymol(mol: QueryMol) -> QueryMol:
    """Return a QueryMol with canonical match exprs and atom-level mapnos."""
    atoms: list[QueryAtom] = []
    for a in mol.atoms:
        expr, mapno = hoist_mapno(a.expr, a.mapno)
        dummy = a.dummy or isinstance(expr, AnyAtom)
        atoms.append(QueryAtom(expr=expr, dummy=dummy, mapno=mapno))
    bonds = tuple(
        QueryBond(b.a, b.b, canonicalize_bond_expr(b.expr)) for b in mol.bonds
    )
    return QueryMol(
        atoms=tuple(atoms),
        bonds=bonds,
        atom_component=mol.atom_component,
        atom_role=mol.atom_role,
        open_rings=tuple(
            OpenRing(r.ring_id, r.atom, canonicalize_bond_expr(r.bond))
            for r in mol.open_rings
        ),
    )
