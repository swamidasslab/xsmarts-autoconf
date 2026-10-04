"""XSMARTS dialect binding: late-bound hybridization and expressibility.

XSMARTS (family ``"xsmarts"``) parses the union of every supported
dialect. The only primitive whose *spelling* means different things in
different dialects is hybridization ``^n`` (docs/smarts_dialects.md,
``hyb.DIGIT_TO_KIND``). XSMARTS binds a digit at parse time only when every
dialect that has ``^n`` agrees on its meaning (today ``^1``–``^3``); the rest
stay :class:`UnboundHybridization` until :func:`bind_hybridization` is called
with the source dialect. After binding, the QueryMol is dialect-independent.
"""

from __future__ import annotations

from dataclasses import replace

from .hyb import DIGIT_TO_KIND, HybKind
from .types import (
    AtomAnd,
    AtomExpr,
    AtomNot,
    AtomOr,
    Hybridization,
    QueryMol,
    Recursive,
    UnboundHybridization,
)

XSMARTS = "xsmarts"

# Open Babel: bare ``^`` means ``^1``.
_BARE_DIGIT = {"openbabel": 1}


class BindError(ValueError):
    """A ``^n`` digit has no meaning in the requested dialect."""


def consistent_digits() -> dict[int, HybKind]:
    """Digits every hybridization dialect defines with the same kind."""
    tables = list(DIGIT_TO_KIND.values())
    common = set.intersection(*(set(t) for t in tables))
    return {d: tables[0][d] for d in sorted(common) if len({t[d] for t in tables}) == 1}


def parse_hybridization(digit: int | None) -> AtomExpr:
    """XSMARTS parse action for ``^n``: bind only dialect-consistent digits."""
    if digit is not None and digit in consistent_digits():
        return Hybridization(consistent_digits()[digit])
    return UnboundHybridization(digit)


def _map_expr(expr: AtomExpr, leaf) -> AtomExpr:
    if isinstance(expr, AtomNot):
        return AtomNot(_map_expr(expr.expr, leaf))
    if isinstance(expr, AtomAnd):
        return AtomAnd(tuple(_map_expr(p, leaf) for p in expr.parts), tight=expr.tight)
    if isinstance(expr, AtomOr):
        return AtomOr(tuple(_map_expr(p, leaf) for p in expr.parts))
    return leaf(expr)


def _leaves(expr: AtomExpr):
    if isinstance(expr, AtomNot):
        yield from _leaves(expr.expr)
    elif isinstance(expr, (AtomAnd, AtomOr)):
        for p in expr.parts:
            yield from _leaves(p)
    else:
        yield expr


def unbound_hybridization(mol: QueryMol) -> tuple[int | None, ...]:
    out: list[int | None] = []
    for a in mol.atoms:
        for leaf in _leaves(a.expr):
            if isinstance(leaf, UnboundHybridization):
                out.append(leaf.digit)
            elif isinstance(leaf, Recursive):
                out.extend(unbound_hybridization(leaf.mol))
    return tuple(out)


def bind_hybridization(mol: QueryMol, dialect: str) -> QueryMol:
    """Replace every UnboundHybridization with ``dialect``'s Hybridization kind."""
    from .canonical import canonicalize_querymol

    table = DIGIT_TO_KIND.get(dialect)

    def leaf(e: AtomExpr) -> AtomExpr:
        if isinstance(e, Recursive):
            return Recursive(mol=_bind(e.mol), anchor=e.anchor)
        if not isinstance(e, UnboundHybridization):
            return e
        if table is None:
            raise BindError(f"dialect {dialect!r} has no hybridization (^n) primitive")
        digit = e.digit if e.digit is not None else _BARE_DIGIT.get(dialect)
        if digit is None:
            raise BindError(f"bare '^' has no meaning in {dialect!r} (Open Babel only)")
        if digit not in table:
            slots = ",".join(f"^{d}" for d in sorted(table))
            raise BindError(f"^{digit} has no meaning in {dialect!r} (slots: {slots})")
        return Hybridization(table[digit])

    def _bind(m: QueryMol) -> QueryMol:
        atoms = tuple(replace(a, expr=_map_expr(a.expr, leaf)) for a in m.atoms)
        return replace(m, atoms=atoms)

    if not mol.unbound_hybridization():
        return mol
    return canonicalize_querymol(_bind(mol))


def dialect_issues(
    mol: QueryMol, dialect: str, *, emulate_extensions: bool = False
) -> list[str]:
    """Every reason ``mol`` cannot be written as ``dialect`` (empty = expressible)."""
    from .write import WriteError, _validate_atom_expr, _validate_bond_expr

    issues: list[str] = []

    def check(m: QueryMol, where: str) -> None:
        for i, a in enumerate(m.atoms):
            for leaf in _leaves(a.expr):
                if isinstance(leaf, Recursive):
                    check(leaf.mol, f"{where}atom {i} $(): ")
                    continue
                try:
                    _validate_atom_expr(leaf, dialect, emulate_extensions=emulate_extensions)  # type: ignore[arg-type]
                except WriteError as e:
                    issues.append(f"{where}atom {i}: {e}")
        for k, b in enumerate(m.bonds):
            try:
                _validate_bond_expr(b.expr, dialect)  # type: ignore[arg-type]
            except WriteError as e:
                issues.append(f"{where}bond {k}: {e}")
        for r in m.open_rings:
            issues.append(
                f"{where}open ring closure {r.ring_id!r} on atom {r.atom}: "
                "resolve it before writing (validator policy)"
            )

    check(mol, "")
    return issues
