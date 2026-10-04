"""Recognize / emit recursive SMARTS that emulate CDK ``i`` / ``iN``.

CDK semantics (Expr): unsaturated = has a double bond or is aromatic;
``iN`` = exactly N double bonds (aromatic counts as ``i1``-style via the
unsaturated OR). Triples are ignored.
"""

from __future__ import annotations

from .types import (
    AnyAtom,
    Aromatic,
    AtomAnd,
    AtomExpr,
    AtomNot,
    AtomOr,
    Count,
    DoubleBond,
    Insaturation,
    QueryAtom,
    Recursive,
)


def _is_any_star(atom: QueryAtom) -> bool:
    return isinstance(atom.expr, AnyAtom)


def double_bond_star_count(rec: Recursive) -> int | None:
    """If ``rec`` is ``[*](=*)…`` with N double spokes from anchor, return N."""
    mol = rec.mol
    if rec.anchor != 0 or mol.n_atoms < 2:
        return None
    if not all(_is_any_star(a) for a in mol.atoms):
        return None
    if mol.atom_role or (mol.atom_component and len(set(mol.atom_component)) > 1):
        return None
    n = mol.n_atoms - 1
    if mol.n_bonds != n:
        return None
    seen: set[int] = set()
    for b in mol.bonds:
        if not isinstance(b.expr, DoubleBond):
            return None
        a, c = b.a, b.b
        if a == rec.anchor:
            other = c
        elif c == rec.anchor:
            other = a
        else:
            return None
        if other == rec.anchor or other in seen or not (0 <= other < mol.n_atoms):
            return None
        seen.add(other)
    if seen != set(range(1, n + 1)) and seen != set(range(mol.n_atoms)) - {rec.anchor}:
        # allow any labeling of neighbors as long as all non-anchor atoms covered
        if seen != set(range(mol.n_atoms)) - {rec.anchor}:
            return None
    return n


def fold_insaturation_patterns(expr: AtomExpr) -> AtomExpr | None:
    """If ``expr`` is a known ``i`` emulation, return :class:`Insaturation`."""
    # [$([*]=*),a] → bare i
    if isinstance(expr, AtomOr) and len(expr.parts) == 2:
        a, b = expr.parts
        if isinstance(a, Aromatic) and isinstance(b, Recursive):
            if double_bond_star_count(b) == 1:
                return Insaturation(Count(defaulted=True))
        if isinstance(b, Aromatic) and isinstance(a, Recursive):
            if double_bond_star_count(a) == 1:
                return Insaturation(Count(defaulted=True))
        # i1: (exact 1 double) OR aromatic
        for p, q in ((a, b), (b, a)):
            if isinstance(p, Aromatic) and _is_exact_double_count(q) == 1:
                return Insaturation(Count(value=1))
            # After folding the exact-1 arm: Or(a, Insaturation(1)) → i1
            if isinstance(p, Aromatic) and isinstance(q, Insaturation):
                if q.count.value == 1 and not q.count.defaulted:
                    return Insaturation(Count(value=1))
                if q.count.defaulted or q.count.value == 0:
                    return Insaturation(Count(defaulted=True))

    # exact N doubles (N >= 2, or N == 1 without aromatic)
    n = _is_exact_double_count(expr)
    if n is not None and n >= 1:
        return Insaturation(Count(value=n))

    return None


def _is_exact_double_count(expr: AtomExpr) -> int | None:
    if not isinstance(expr, AtomAnd) or len(expr.parts) != 2:
        return None
    pos: Recursive | None = None
    neg: Recursive | None = None
    for p in expr.parts:
        if isinstance(p, Recursive):
            pos = p
        elif isinstance(p, AtomNot) and isinstance(p.expr, Recursive):
            neg = p.expr
        else:
            return None
    if pos is None or neg is None:
        return None
    n = double_bond_star_count(pos)
    m = double_bond_star_count(neg)
    if n is None or m is None or m != n + 1:
        return None
    return n


def insat_smarts_open(expr: Insaturation) -> str:
    """SMARTS spelling of ``i`` emulation (inner bracket contents)."""
    if expr.count.defaulted or expr.count.value == 0:
        return "$([*]=*),a"
    n = expr.count.value
    assert n is not None
    if n == 1:
        return "$([*]=*)&!$([*](=*)(=*)),a"
    ge = "(=*)" * n
    gt = "(=*)" * (n + 1)
    return f"$([*]{ge})&!$([*]{gt})"
