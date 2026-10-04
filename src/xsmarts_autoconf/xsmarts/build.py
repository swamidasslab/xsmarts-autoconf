"""Build a QueryMol graph from a SMARTS Lark parse tree.

QueryMol is a graph whose atoms/bonds appear in SMARTS serial order. Each
node/edge ``expr`` stores typed *match constraints* derived from the SMARTS
(counts, element identity, logic, …), not the raw token text. Atom maps
(``:n``) are stored on :attr:`QueryAtom.mapno`, not in the match expression.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable

from lark import Lark, Token, Transformer, Tree, v_args

from .canonical import canonicalize_atom_expr, canonicalize_querymol
from .parse import Family, parse_tree
from .types import (
    Aliphatic,
    AliphaticHeteroNeighbors,
    AnyAtom,
    AnyBond,
    Aromatic,
    AromaticBond,
    AtomAnd,
    AtomExpr,
    AtomMap,
    AtomNot,
    AtomOr,
    AtomicNumber,
    BondAnd,
    BondExpr,
    BondNot,
    BondOr,
    Charge,
    Chirality,
    Connectivity,
    Count,
    DativeLeft,
    DativeRight,
    Degree,
    DoubleBond,
    DownBond,
    DownOrUnspec,
    Element,
    HeteroAny,
    HeteroNeighbors,
    Hybridization,
    ImplicitH,
    Insaturation,
    IntRange,
    Isotope,
    NonHDegree,
    OpenRing,
    PeriodicGroup,
    QuadrupleBond,
    QueryAtom,
    QueryBond,
    QueryMol,
    Recursive,
    RingBond,
    RingConnectivity,
    RingMembership,
    RingSize,
    RingSizeK,
    Role,
    SingleBond,
    SingleOrAromatic,
    TotalH,
    TripleBond,
    UpBond,
    UpOrUnspec,
    Valence,
)

_GRAMMAR_DIR = Path(__file__).resolve().parent / "grammars"
_AROMATIC_SYMBOLS = frozenset({"b", "c", "n", "o", "p", "s", "se", "as"})


@lru_cache(maxsize=None)
def _bond_parser() -> Lark:
    return Lark.open(
        str(_GRAMMAR_DIR / "bond_expr.lark"),
        parser="lalr",
        maybe_placeholders=False,
    )


def _parse_range(text: str) -> IntRange:
    inner = text.strip("{}")
    if inner.startswith("-"):
        return IntRange(min=None, max=int(inner[1:]))
    if inner.endswith("-"):
        return IntRange(min=int(inner[:-1]), max=None)
    lo, _, hi = inner.partition("-")
    return IntRange(min=int(lo), max=int(hi))


def _count(num: Token | None, *, default: int | None = 1) -> Count:
    """Parse an optional SMARTS count; omitted number uses Daylight default.

    ``default=1`` matches D/v/X/H (exactly one). Pass ``default=None`` for
    predicates whose bare form means “any” (R, r) and keep ``defaulted=True``.
    """
    if num is None:
        if default is None:
            return Count(defaulted=True)
        return Count(value=default)
    return Count(value=int(num))


def _symbol_constraint(sym: str) -> AtomExpr:
    """Map an organic/element symbol token to an element/dummy constraint."""
    if sym == "*":
        return AnyAtom()
    if sym in _AROMATIC_SYMBOLS or (len(sym) <= 2 and sym.islower()):
        return Element(symbol=sym, aromatic=True)
    return Element(symbol=sym, aromatic=False)


def _is_element_like(expr: AtomExpr) -> bool:
    return isinstance(
        expr, (Element, AtomicNumber, Aromatic, Aliphatic, AnyAtom, HeteroAny)
    )


def _is_bare_h(expr: AtomExpr) -> bool:
    return isinstance(expr, Element) and expr.symbol == "H" and expr.aromatic is False


def _has_atom_identity(expr: AtomExpr) -> bool:
    """True if expr (possibly under OR/AND/NOT) names a non-H atom identity."""
    if _is_bare_h(expr):
        return False
    if _is_element_like(expr):
        return True
    if isinstance(expr, AtomOr):
        return any(_has_atom_identity(p) for p in expr.parts)
    if isinstance(expr, AtomAnd):
        return any(_has_atom_identity(p) for p in expr.parts)
    if isinstance(expr, AtomNot):
        return _has_atom_identity(expr.expr)
    return False


def _rewrite_bare_h_to_total_h(expr: AtomExpr) -> AtomExpr:
    """Replace bare element-H with TotalH(1) throughout an expression."""
    if _is_bare_h(expr):
        return TotalH(Count(value=1))
    if isinstance(expr, AtomAnd):
        return AtomAnd(
            tuple(_rewrite_bare_h_to_total_h(p) for p in expr.parts),
            tight=expr.tight,
        )
    if isinstance(expr, AtomOr):
        return AtomOr(tuple(_rewrite_bare_h_to_total_h(p) for p in expr.parts))
    if isinstance(expr, AtomNot):
        return AtomNot(_rewrite_bare_h_to_total_h(expr.expr))
    return expr


def _contains_bare_h(expr: AtomExpr) -> bool:
    if _is_bare_h(expr):
        return True
    if isinstance(expr, AtomAnd):
        return any(_contains_bare_h(p) for p in expr.parts)
    if isinstance(expr, AtomOr):
        return any(_contains_bare_h(p) for p in expr.parts)
    if isinstance(expr, AtomNot):
        return _contains_bare_h(expr.expr)
    return False


def _without_atom_maps(expr: AtomExpr) -> AtomExpr | None:
    """Drop AtomMap nodes; ``None`` if nothing remains."""
    if isinstance(expr, AtomMap):
        return None
    if isinstance(expr, AtomAnd):
        parts = [p for p in (_without_atom_maps(x) for x in expr.parts) if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else AtomAnd(tuple(parts), tight=expr.tight)
    if isinstance(expr, AtomOr):
        parts = [p for p in (_without_atom_maps(x) for x in expr.parts) if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else AtomOr(tuple(parts))
    if isinstance(expr, AtomNot):
        inner = _without_atom_maps(expr.expr)
        return AtomNot(inner) if inner is not None else None
    return expr


def _rewrite_h_constraints(expr: AtomExpr) -> AtomExpr:
    """Bare ``H`` is TotalH(1) unless the bracket is only hydrogen (plus map).

    Matches RDKit/chematic: ``[C,H]`` / ``[a,H:1]`` use H-count, while ``[H]``
    / ``[H:1]`` stay element hydrogen.
    """
    core = _without_atom_maps(expr)
    if core is not None and _contains_bare_h(core) and not _is_bare_h(core):
        return _rewrite_bare_h_to_total_h(expr)
    if isinstance(expr, AtomAnd):
        return AtomAnd(
            tuple(_rewrite_h_constraints(p) for p in expr.parts),
            tight=expr.tight,
        )
    if isinstance(expr, AtomOr):
        return AtomOr(tuple(_rewrite_h_constraints(p) for p in expr.parts))
    if isinstance(expr, AtomNot):
        return AtomNot(_rewrite_h_constraints(expr.expr))
    return expr


# Returned by ``atom_class`` so ``:n`` never enters AtomExpr; filtered in And/Or.
_MAPNO_SKIP = object()


def _without_mapno_skip(parts: list) -> list:
    return [p for p in parts if p is not _MAPNO_SKIP]


def _flatten_and(parts: list[AtomExpr], *, tight: bool) -> AtomExpr:
    flat: list[AtomExpr] = []
    for p in _without_mapno_skip(parts):
        if isinstance(p, AtomAnd) and p.tight == tight:
            flat.extend(p.parts)
        else:
            flat.append(p)
    if not flat:
        return AnyAtom()
    return flat[0] if len(flat) == 1 else AtomAnd(tuple(flat), tight=tight)


def _flatten_or(parts: list[AtomExpr]) -> AtomExpr:
    flat: list[AtomExpr] = []
    for p in _without_mapno_skip(parts):
        if isinstance(p, AtomOr):
            flat.extend(p.parts)
        else:
            flat.append(p)
    if not flat:
        return AnyAtom()
    return flat[0] if len(flat) == 1 else AtomOr(tuple(flat))


def _flatten_bond_and(parts: list[BondExpr], *, tight: bool) -> BondExpr:
    flat: list[BondExpr] = []
    for p in parts:
        if isinstance(p, BondAnd) and p.tight == tight:
            flat.extend(p.parts)
        else:
            flat.append(p)
    return flat[0] if len(flat) == 1 else BondAnd(tuple(flat), tight=tight)


def _flatten_bond_or(parts: list[BondExpr]) -> BondExpr:
    flat: list[BondExpr] = []
    for p in parts:
        if isinstance(p, BondOr):
            flat.extend(p.parts)
        else:
            flat.append(p)
    return flat[0] if len(flat) == 1 else BondOr(tuple(flat))


class _BondConstraintBuilder(Transformer):
    def single(self, _):
        return SingleBond()

    def double(self, _):
        return DoubleBond()

    def triple(self, _):
        return TripleBond()

    def quadruple(self, _):
        return QuadrupleBond()

    def aromatic(self, _):
        return AromaticBond()

    def any_bond(self, _):
        return AnyBond()

    def ring_bond(self, _):
        return RingBond()

    def up(self, _):
        return UpBond()

    def down(self, _):
        return DownBond()

    def up_or_unspec(self, _):
        return UpOrUnspec()

    def down_or_unspec(self, _):
        return DownOrUnspec()

    def dative_right(self, _):
        return DativeRight()

    def dative_left(self, _):
        return DativeLeft()

    def bond_not_op(self, items):
        return BondNot(items[0])

    def bond_impl_and(self, items):
        return _flatten_bond_and(list(items), tight=True)

    def bond_high_and(self, items):
        return _flatten_bond_and(list(items), tight=True)

    def bond_or_op(self, items):
        return _flatten_bond_or(list(items))

    def bond_low_and(self, items):
        return _flatten_bond_and(list(items), tight=False)

    def start(self, items):
        return items[0]


def parse_bond_expr(text: str | None) -> BondExpr:
    """Parse a bond-expression string into bond match constraints."""
    if not text:
        return SingleOrAromatic()
    return _BondConstraintBuilder().transform(_bond_parser().parse(text))


def _parse_chirality(spec: str) -> Chirality:
    """Turn a chiral token into a structured stereo constraint."""
    or_unspecified = spec.endswith("?")
    body = spec[:-1] if or_unspecified else spec
    if body == "@":
        return Chirality(
            clockwise=False, class_=None, permutation=None, or_unspecified=or_unspecified
        )
    if body == "@@":
        return Chirality(
            clockwise=True, class_=None, permutation=None, or_unspecified=or_unspecified
        )
    # @TH1, @AL2, @SP3, @TB10, @OH30, @TH?, …
    rest = body[1:]
    class_map = {
        "TH": "tetrahedral",
        "AL": "allene",
        "SP": "square_planar",
        "TB": "trigonal_bipyramidal",
        "OH": "octahedral",
    }
    for prefix, name in class_map.items():
        if rest.startswith(prefix):
            tail = rest[len(prefix) :]
            perm = int(tail) if tail.isdigit() else None
            return Chirality(
                clockwise=None,
                class_=name,  # type: ignore[arg-type]
                permutation=perm,
                or_unspecified=or_unspecified or tail == "?",
            )
    return Chirality(
        clockwise=False, class_=None, permutation=None, or_unspecified=or_unspecified
    )


def _ext_count(items: tuple) -> Count:
    if not items:
        return Count(defaulted=True)
    it = items[0]
    if isinstance(it, Token):
        s = str(it)
        if s.startswith("{"):
            return Count(range=_parse_range(s))
        return Count(value=int(s))
    return Count(defaulted=True)


def _ranged_constraint(text: str) -> AtomExpr:
    letter = text[0]
    if letter in "+-":
        rng = _parse_range(text[1:])
        sign = 1 if letter == "+" else -1
        if rng.min is not None and rng.max is not None:
            return AtomOr(
                tuple(Charge(sign * v) for v in range(rng.min, rng.max + 1))
            )
        v = rng.min if rng.min is not None else rng.max
        assert v is not None
        return Charge(sign * v)
    count = Count(range=_parse_range(text[1:]))
    mapping: dict[str, Callable[[Count], AtomExpr]] = {
        "D": Degree,
        "h": ImplicitH,
        "x": RingConnectivity,
        "X": Connectivity,
        "R": RingMembership,
        "r": RingSize,
        "v": Valence,
        "z": HeteroNeighbors,
        "Z": AliphaticHeteroNeighbors,
        "k": RingSizeK,
        "d": NonHDegree,
    }
    ctor = mapping.get(letter)
    if ctor is None:
        if letter == "G":
            n = count.range.min if count.range and count.range.min is not None else 0
            return PeriodicGroup(n=n)
        return Degree(count)
    return ctor(count)


@v_args(inline=True)
class _AtomConstraintBuilder(Transformer):
    """Reduce bracket contents to typed atom-match constraints."""

    def __init__(self, family: Family = "opensmarts") -> None:
        super().__init__()
        self.family = family
        self.mapno: int | None = None
        """Captured from ``:n``; never placed in the match expression."""

    def _transform_children(self, children):
        # Replace recursive_smarts with finished Recursive constraints *before*
        # the default Transformer descends (otherwise SYMBOL inside `$()` becomes
        # Element and the nested graph cannot be built).
        prepared = []
        for c in children:
            if isinstance(c, Tree) and _rule(c) == "recursive_smarts":
                reaction = c.children[0]
                assert isinstance(reaction, Tree)
                prepared.append(
                    Recursive(
                        mol=_GraphBuilder(self.family).build_reaction(reaction),
                        anchor=0,
                    )
                )
            else:
                prepared.append(c)
        return super()._transform_children(prepared)

    def atom_expression(self, expr):
        if expr is _MAPNO_SKIP:
            return AnyAtom()
        return _rewrite_h_constraints(expr)

    def atom_not_op(self, expr):
        if expr is _MAPNO_SKIP:
            return AtomNot(AnyAtom())
        return AtomNot(expr)

    def atom_impl_and(self, a, b):
        return _flatten_and([a, b], tight=True)

    def atom_high_and(self, a, b):
        return _flatten_and([a, b], tight=True)

    def atom_or_op(self, a, b):
        return _flatten_or([a, b])

    def atom_low_and(self, a, b):
        return _flatten_and([a, b], tight=False)

    def isotope(self, num: Token):
        return Isotope(int(num))

    def atomic_number(self, num: Token):
        return AtomicNumber(int(num))

    def SYMBOL(self, tok: Token):
        return _symbol_constraint(str(tok))

    def aromatic_any(self, *_):
        return Aromatic()

    def aliphatic_any(self, *_):
        return Aliphatic()

    def degree(self, num: Token | None = None):
        return Degree(_count(num))

    def valence(self, num: Token | None = None):
        return Valence(_count(num))

    def connectivity(self, num: Token | None = None):
        return Connectivity(_count(num))

    def TOTAL_HCOUNT(self, tok: Token):
        return TotalH(Count(value=int(str(tok)[1:])))

    def total_hcount(self, constraint):
        return constraint

    def IMPLICIT_HCOUNT(self, tok: Token):
        return ImplicitH(Count(value=int(str(tok)[1:])))

    def implicit_hcount(self, constraint):
        return constraint

    def implicit_h_default(self, *_):
        return ImplicitH(Count(defaulted=True))

    def ring_membership(self, num: Token | None = None):
        return RingMembership(_count(num, default=None))

    def ring_size(self, num: Token | None = None):
        return RingSize(_count(num, default=None))

    def ring_connectivity(self, num: Token | None = None):
        # Daylight bare ``x``: at least one ring connection.
        return RingConnectivity(_count(num, default=None))

    def PLUSPLUS(self, _tok=None):
        # Chematic ≥1.0.30: ``++`` matches Charge(+2) (Daylight-compatible).
        return Charge(2)

    def MINUSMINUS(self, _tok=None):
        return Charge(-2)

    def PLUS(self, _tok=None):
        return "+"

    def MINUS(self, _tok=None):
        return "-"

    def charge(self, *items):
        # After terminal methods: Charge, AtomAnd for chematic ``++``, or
        # ("+",) / ("+", n) / ("-",) / ("-", n)
        if len(items) == 1 and isinstance(items[0], (Charge, AtomAnd)):
            return items[0]
        if not items:
            return Charge(1)
        sign = items[0]
        if isinstance(sign, (Charge, AtomAnd)):
            return sign
        mag = 1
        if len(items) > 1 and items[1] is not None:
            mag = int(items[1])
        if sign == "-":
            return Charge(-mag)
        return Charge(mag)

    def CHIRAL(self, tok: Token):
        return _parse_chirality(str(tok))

    def chiral(self, constraint):
        return constraint

    def atom_class(self, num: Token):
        # Atom maps are tracking labels, not match constraints — record on the
        # builder and omit from AtomExpr (And/Or drop ``_MAPNO_SKIP``).
        self.mapno = int(num)
        return _MAPNO_SKIP

    def recursive_smarts(self, nested: Recursive):
        # Usually replaced in _transform_children; keep as identity fallback.
        return nested

    def HYBRID(self, tok: Token):
        from .hyb import digit_to_kind

        n = int(str(tok)[1:])
        if self.family == "xsmarts":
            from .dialect import parse_hybridization

            return parse_hybridization(n)  # late-bound unless all dialects agree
        return Hybridization(digit_to_kind(self.family, n))

    def BARE_HYB(self, _tok: Token):
        from .hyb import digit_to_kind

        if self.family == "xsmarts":
            from .dialect import parse_hybridization

            return parse_hybridization(None)
        # Open Babel: bare ``^`` means ``^1`` (sp).
        return Hybridization(digit_to_kind(self.family, 1))

    def hybridization(self, constraint):
        return constraint

    def hetero_neighbors(self, *items):
        return HeteroNeighbors(_ext_count(items))

    def aliphatic_hetero_neighbors(self, *items):
        return AliphaticHeteroNeighbors(_ext_count(items))

    def non_h_degree(self, *items):
        # RDKit bare ``d`` means exactly one (like ``D``), not “defaulted”.
        if not items:
            return NonHDegree(Count(value=1))
        return NonHDegree(_ext_count(items))

    def ring_size_k(self, *items):
        return RingSizeK(_ext_count(items))

    def hetero_any(self, *_):
        return HeteroAny()

    def periodic_group(self, num: Token):
        return PeriodicGroup(n=int(num), hashed=False)

    def periodic_group_hashed(self, num: Token):
        # Own alias: the anonymous "#G" literal is filtered from the tree.
        return PeriodicGroup(n=int(num), hashed=True)

    def insaturation(self, *items):
        return Insaturation(_ext_count(items))

    def RANGED_ATOM_QUERY(self, tok: Token):
        return _ranged_constraint(str(tok))

    def ranged_query(self, constraint):
        return constraint


def _rule(tree: Tree) -> str:
    """Local rule name (strip Lark ``%import`` namespace prefixes)."""
    return str(tree.data).rsplit("__", 1)[-1]


def _strip_namespaces(node: Tree | Token) -> Tree | Token:
    """Drop Lark ``%import`` prefixes on rule *and* token names."""
    if isinstance(node, Token):
        typ = str(node.type).rsplit("__", 1)[-1]
        if typ == node.type:
            return node
        return Token(typ, node.value, node.start_pos, node.line, node.column, node.end_line, node.end_column, node.end_pos)
    assert isinstance(node, Tree)
    return Tree(
        _rule(node),
        [_strip_namespaces(c) if isinstance(c, (Tree, Token)) else c for c in node.children],
        meta=getattr(node, "meta", None),
    )


def _parse_bracket_atom(
    bracket: Tree, family: Family = "opensmarts"
) -> tuple[AtomExpr, int | None]:
    """`bracket_atom` → ``(match_expr, mapno)``. ``:n`` never enters ``expr``."""
    bracket = _strip_namespaces(bracket)  # type: ignore[assignment]
    # children: atom_expression (literals '[' ']' omitted)
    expr_node = bracket.children[0]
    if not isinstance(expr_node, Tree):
        # atom_expression inlined
        expr_node = Tree("atom_expression", list(bracket.children))
    builder = _AtomConstraintBuilder(family)
    result = builder.transform(expr_node)
    if isinstance(result, Tree):
        result = builder.transform(result)
    if result is _MAPNO_SKIP:
        result = AnyAtom()
    assert isinstance(result, (AtomAnd, AtomOr, AtomNot, Recursive)) or not isinstance(
        result, Tree
    )
    expr = canonicalize_atom_expr(_rewrite_h_constraints(result))  # type: ignore[arg-type]
    return expr, builder.mapno


def _bracket_constraints(bracket: Tree, family: Family = "opensmarts") -> AtomExpr:
    """`bracket_atom` → match constraints only (mapno discarded)."""
    expr, _mapno = _parse_bracket_atom(bracket, family)
    return expr


def _query_atom_from_tree(atom_tree: Tree, family: Family = "opensmarts") -> QueryAtom:
    child = atom_tree.children[0]
    if isinstance(child, Token):
        expr = _symbol_constraint(str(child))
        return QueryAtom(expr=expr, dummy=isinstance(expr, AnyAtom))
    if not isinstance(child, Tree):
        raise TypeError(f"unexpected atom child type {type(child)!r}: {child!r}")
    name = _rule(child)
    if name == "atom":
        return _query_atom_from_tree(child, family)
    if name == "bracket_atom":
        expr, mapno = _parse_bracket_atom(child, family)
        dummy = isinstance(expr, AnyAtom) or (
            isinstance(expr, AtomAnd) and any(isinstance(p, AnyAtom) for p in expr.parts)
        )
        return QueryAtom(expr=expr, dummy=dummy, mapno=mapno)
    # Organic / wildcard symbol promoted to its own tree node in some imports.
    if name == "SYMBOL" or str(child.data) == "SYMBOL":
        expr = _symbol_constraint(str(child.children[0]) if child.children else str(child))
        return QueryAtom(expr=expr, dummy=isinstance(expr, AnyAtom))
    raise TypeError(f"unexpected atom node {child.data!r}")


class _GraphBuilder:
    """
    Walk a parse tree into a QueryMol.

    Atoms are appended in SMARTS left-to-right order. Bonds are appended when
    first fully known (new atom edge immediately; ring closure at the closing
    digit). Either endpoint may be a dummy atom.
    """

    def __init__(self, family: Family = "opensmarts") -> None:
        self.family = family
        self.atoms: list[QueryAtom] = []
        self.bonds: list[QueryBond] = []
        self.atom_component: list[int] = []
        self.atom_role: list[Role] = []
        self._rings: dict[str, tuple[int, BondExpr]] = {}
        self._open_rings: list[OpenRing] = []
        self._component = 0
        self._role: Role = "reactant"
        self._is_reaction = False

    def build_reaction(self, tree: Tree) -> QueryMol:
        tree = _strip_namespaces(tree)  # type: ignore[assignment]
        if _rule(tree) == "start":
            tree = tree.children[0]
            assert isinstance(tree, Tree)
        kind = _rule(tree)
        if kind == "reaction":
            self._reaction(tree)
        elif kind == "role":
            self._role_node(tree, "reactant")
        elif kind == "mol":
            self._mol(tree)
        else:
            raise ValueError(f"unexpected root {tree.data}")
        roles = tuple(self.atom_role) if self._is_reaction else ()
        # Unclosed ring digits are data, not errors: validators decide.
        self._close_role_rings()
        open_rings = tuple(self._open_rings)
        return QueryMol(
            atoms=tuple(self.atoms),
            bonds=tuple(self.bonds),
            atom_component=tuple(self.atom_component),
            atom_role=roles,
            open_rings=open_rings,
        )

    def _reaction(self, tree: Tree) -> None:
        role_nodes = [
            c for c in tree.children if isinstance(c, Tree) and _rule(c) == "role"
        ]
        if len(role_nodes) == 1:
            self._role_node(role_nodes[0], "reactant")
            return
        self._is_reaction = True
        if len(role_nodes) == 2:
            # reactants >> products
            self._role_node(role_nodes[0], "reactant")
            self._bump_component()
            self._role_node(role_nodes[1], "product")
            return
        order: list[Role] = ["reactant", "agent", "product"]
        for i, node in enumerate(role_nodes[:3]):
            if i:
                self._bump_component()
            self._role_node(node, order[i])

    def _bump_component(self) -> None:
        if self.atom_component:
            self._component = max(self.atom_component) + 1
        else:
            self._component = 0

    def _close_role_rings(self) -> None:
        """Ring digits do not cross ``>``: park the role's unclosed ones."""
        self._open_rings.extend(
            OpenRing(ring_id=rid, atom=atom, bond=bond)
            for rid, (atom, bond) in self._rings.items()
        )
        self._rings = {}

    def _role_node(self, tree: Tree, role: Role) -> None:
        self._close_role_rings()
        self._role = role
        first = True
        for child in tree.children:
            if not isinstance(child, Tree) or _rule(child) != "mol":
                continue
            if not first:
                self._bump_component()
            first = False
            self._mol(child)

    def _mol(self, tree: Tree) -> None:
        # mol: first_atom + inlined _branching_chain → first_atom, chain?, branch, …
        first = tree.children[0]
        assert isinstance(first, Tree)  # first_atom
        atom_node = first.children[0]
        assert isinstance(atom_node, Tree)
        head = self._add_atom(atom_node)
        for child in tree.children[1:]:
            if not isinstance(child, Tree):
                continue
            name = _rule(child)
            if name == "chain":
                head = self._chain(child, head)
            elif name == "branch":
                # branch does not advance the head for following siblings
                self._branch(child, head)

    def _add_atom(self, atom_tree: Tree) -> int:
        qa = _query_atom_from_tree(atom_tree, self.family)
        idx = len(self.atoms)
        self.atoms.append(qa)
        self.atom_component.append(self._component)
        self.atom_role.append(self._role)
        return idx

    def _branch(self, tree: Tree, head: int) -> None:
        # branch: open + inlined _branching_chain + close
        branch_head = head
        for child in tree.children:
            if not isinstance(child, Tree):
                continue
            name = _rule(child)
            if name == "chain":
                branch_head = self._chain(child, branch_head)
            elif name == "branch":
                self._branch(child, branch_head)
            elif name == "_branching_chain":
                self._branching(child, branch_head)

    def _branching(self, tree: Tree, head: int) -> None:
        cur = head
        for child in tree.children:
            if not isinstance(child, Tree):
                continue
            name = _rule(child)
            if name == "chain":
                cur = self._chain(child, cur)
            elif name == "branch":
                self._branch(child, cur)

    def _chain(self, tree: Tree, head: int) -> int:
        cur = head
        for ba in tree.children:
            if isinstance(ba, Tree) and _rule(ba) == "bond_atom":
                cur = self._bond_atom(ba, cur)
        return cur

    def _bond_atom(self, tree: Tree, prev: int) -> int:
        bond_expr: BondExpr = SingleOrAromatic()
        target: Tree | Token | None = None
        for child in tree.children:
            if isinstance(child, Tree) and _rule(child) == "bond":
                bond_expr = parse_bond_expr(str(child.children[0]))
            elif isinstance(child, (Tree, Token)):
                target = child
        assert target is not None
        if isinstance(target, Tree) and _rule(target) == "ring":
            self._ring_closure(target, prev, bond_expr)
            return prev
        if isinstance(target, Token):
            atom_tree = Tree("atom", [target])
        elif _rule(target) == "atom":
            atom_tree = target
        else:
            atom_tree = Tree("atom", [target])
        nxt = self._add_atom(atom_tree)
        self.bonds.append(QueryBond(prev, nxt, bond_expr))
        return nxt

    def _ring_closure(self, tree: Tree, atom_idx: int, bond_expr: BondExpr) -> None:
        rid = str(tree.children[0]).lstrip("%")
        if rid not in self._rings:
            self._rings[rid] = (atom_idx, bond_expr)
            return
        other, other_bond = self._rings.pop(rid)
        expr = _merge_ring_bonds(other_bond, bond_expr)
        self.bonds.append(QueryBond(other, atom_idx, expr))


def _merge_ring_bonds(a: BondExpr, b: BondExpr) -> BondExpr:
    if isinstance(a, SingleOrAromatic):
        return b
    if isinstance(b, SingleOrAromatic):
        return a
    if a == b:
        return a
    return BondAnd((a, b), tight=True)


def build_querymol(smarts: str, family: Family = "opensmarts") -> QueryMol:
    """Parse SMARTS and return a typed QueryMol graph (SMARTS atom/bond order)."""
    return canonicalize_querymol(
        _GraphBuilder(family).build_reaction(parse_tree(smarts, family))
    )


def build_atom_expr(smarts: str, family: Family = "opensmarts") -> AtomExpr:
    """Parse a bracket atom or bare atom-expression into match constraints.

    Atom maps (``:n``) are not match constraints and are stripped. Prefer
    :func:`build_querymol` when map numbers matter.
    """
    text = smarts.strip()
    if text.startswith("[") and text.endswith("]"):
        tree = parse_tree(text, family, start="bracket_atom")
        return _bracket_constraints(tree, family)
    tree = parse_tree(text, family, start="atom_expression")
    tree = _strip_namespaces(tree)  # type: ignore[assignment]
    builder = _AtomConstraintBuilder(family)
    result = builder.transform(tree)
    if isinstance(result, Tree):
        result = builder.transform(result)
    if result is _MAPNO_SKIP:
        result = AnyAtom()
    return canonicalize_atom_expr(_rewrite_h_constraints(result))  # type: ignore[arg-type]


def querymol_from_tree(tree: Tree, family: Family = "opensmarts") -> QueryMol:
    """Convert an already-parsed SMARTS tree to a QueryMol graph."""
    return canonicalize_querymol(_GraphBuilder(family).build_reaction(tree))
