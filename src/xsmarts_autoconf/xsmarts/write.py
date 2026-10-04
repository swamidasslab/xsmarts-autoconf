"""Serialize QueryMol / AtomExpr / BondExpr to SMARTS for a dialect."""

from __future__ import annotations

from contextvars import ContextVar

from .parse import FAMILIES, Family
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
    UnboundHybridization,
    ImplicitH,
    Insaturation,
    IntRange,
    Isotope,
    NonHDegree,
    PeriodicGroup,
    QuadrupleBond,
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

_ORGANIC = frozenset("B C N O S P F Cl Br I b c n o s p".split())

# When False, AND parts are always joined with ``;`` / ``&`` (no juxtaposition).
_ALLOW_JUXTAPOSE: ContextVar[bool] = ContextVar("allow_juxtapose", default=True)

# Constraint types that are not in OpenSMARTS / Daylight core.
_RDKIT_ONLY = (
    HeteroNeighbors,
    AliphaticHeteroNeighbors,
    NonHDegree,
)
_CDK_ONLY = (
    HeteroAny,
    PeriodicGroup,
)
# Insaturation (``i``) is CDK-native; recursive SMARTS emulation requires
# ``emulate_extensions=True``.
# RDKit + chematic (chematic has kN / ^n; no z/Z/d/ranges).
_RDKIT_OR_CHEMATIC = (RingSizeK,)


class WriteError(ValueError):
    """Expression cannot be represented in the requested SMARTS dialect."""


def write_smarts(
    mol: QueryMol,
    family: Family = "opensmarts",
    *,
    emulate_extensions: bool = False,
) -> str:
    """Write a QueryMol graph as SMARTS in ``family`` dialect.

    Parameters
    ----------
    emulate_extensions:
        If True, rewrite selected foreign primitives into portable SMARTS
        (currently CDK ``i``/``iN`` → recursive double/aromatic patterns).
        Default False: unsupported primitives raise :class:`WriteError`.

    The writer may juxtapose tokens for terseness, then re-parses the result
    and checks that the QueryMol constraints match. On mismatch it retries
    without juxtaposition; if that still fails it raises :class:`WriteError`.
    """
    _check_family(family)
    if mol.open_rings:
        raise WriteError(
            f"{len(mol.open_rings)} unclosed ring closure(s); resolve "
            "QueryMol.open_rings before writing (validator policy)"
        )
    if not mol.atoms:
        return ""

    def emit(*, juxtapose: bool) -> str:
        token = _ALLOW_JUXTAPOSE.set(juxtapose)
        try:
            if mol.atom_role:
                return _write_reaction(
                    mol, family, emulate_extensions=emulate_extensions
                )
            comps = _components(mol)
            return ".".join(
                _write_component(
                    mol, atoms, family, emulate_extensions=emulate_extensions
                )
                for atoms in comps
            )
        finally:
            _ALLOW_JUXTAPOSE.reset(token)

    out = emit(juxtapose=True)
    if _smarts_roundtrips(mol, out, family):
        return out
    out = emit(juxtapose=False)
    if _smarts_roundtrips(mol, out, family):
        return out
    raise WriteError(
        f"write/parse round-trip failed for family={family!r}: produced {out!r}"
    )


def _norm_atom_component(mol: QueryMol) -> tuple[int, ...]:
    """Empty component tuple means a single component (all zeros)."""
    if not mol.atoms:
        return ()
    if not mol.atom_component:
        return tuple(0 for _ in mol.atoms)
    return mol.atom_component


def _smarts_roundtrips(mol: QueryMol, smarts: str, family: Family) -> bool:
    """True if ``smarts`` re-parses to the same canonical QueryMol constraints."""
    from .build import build_querymol
    from .canonical import canonicalize_querymol
    from .parse import ParseError

    try:
        got = build_querymol(smarts, family)
    except (ParseError, ValueError, TypeError, WriteError):
        return False
    left = canonicalize_querymol(mol)
    return (
        left.atoms == got.atoms
        and left.bonds == got.bonds
        and left.atom_role == got.atom_role
        and _norm_atom_component(left) == _norm_atom_component(got)
    )


def _atom_expr_roundtrips(expr: AtomExpr, smarts: str, family: Family) -> bool:
    """True if ``smarts`` re-parses via ``bracket_atom``/``atom_expression`` start."""
    from .build import build_atom_expr
    from .canonical import canonicalize_atom_expr
    from .parse import ParseError

    try:
        got = build_atom_expr(smarts, family)
    except (ParseError, ValueError, TypeError, WriteError):
        return False
    return canonicalize_atom_expr(expr) == got


def write_atom_expr(
    expr: AtomExpr,
    family: Family = "opensmarts",
    *,
    bracketed: bool | None = None,
    emulate_extensions: bool = False,
) -> str:
    """
    Translate an :class:`AtomExpr` constraint tree to SMARTS.

    Parameters
    ----------
    bracketed:
        ``True`` → always ``[...]``; ``False`` → never; ``None`` → bracket
        unless the expr is a bare organic / ``*`` symbol.
    emulate_extensions:
        See :func:`write_smarts`.
    """
    from .types import QueryAtom, QueryMol

    _check_family(family)
    _validate_atom_expr(expr, family, emulate_extensions=emulate_extensions)
    if bracketed is False:
        organic = _as_organic(expr)
        if organic is not None:
            return organic
        raise WriteError(
            "write_atom_expr(bracketed=False) requires a bare organic / * symbol"
        )

    if bracketed is None:
        return write_smarts(
            QueryMol(atoms=(QueryAtom(expr=expr),)),
            family,
            emulate_extensions=emulate_extensions,
        )

    # bracketed=True: force ``[...]``; verify with ``bracket_atom`` start symbol.
    def emit(*, juxtapose: bool) -> str:
        token = _ALLOW_JUXTAPOSE.set(juxtapose)
        try:
            return (
                "["
                + _atom_expr_to_smarts(
                    expr, "low", family, emulate_extensions=emulate_extensions
                )
                + "]"
            )
        finally:
            _ALLOW_JUXTAPOSE.reset(token)

    out = emit(juxtapose=True)
    if _atom_expr_roundtrips(expr, out, family):
        return out
    out = emit(juxtapose=False)
    if _atom_expr_roundtrips(expr, out, family):
        return out
    raise WriteError(
        f"write/parse round-trip failed for family={family!r}: produced {out!r}"
    )

def write_bond_expr(expr: BondExpr, family: Family = "opensmarts") -> str:
    """
    Translate a :class:`BondExpr` constraint tree to SMARTS.

    Omitted / default single-or-aromatic bonds serialize as ``\"\"``.
    Dative ``->`` / ``<-`` require ``rdkit`` (also accepted when writing
    ``cdk`` as a practical superset for bond glyphs).
    """
    _check_family(family)
    _validate_bond_expr(expr, family)
    return _bond_to_smarts(expr, family)


def _check_family(family: Family) -> None:
    if family not in FAMILIES:
        raise ValueError(f"unknown SMARTS family {family!r}; choose from {FAMILIES}")


def _validate_atom_expr(
    expr: AtomExpr,
    family: Family,
    *,
    emulate_extensions: bool = False,
) -> None:
    if isinstance(expr, AtomNot):
        _validate_atom_expr(expr.expr, family, emulate_extensions=emulate_extensions)
        return
    if isinstance(expr, (AtomAnd, AtomOr)):
        for p in expr.parts:
            _validate_atom_expr(p, family, emulate_extensions=emulate_extensions)
        return
    if isinstance(expr, Recursive):
        for atom in expr.mol.atoms:
            _validate_atom_expr(
                atom.expr, family, emulate_extensions=emulate_extensions
            )
        for bond in expr.mol.bonds:
            _validate_bond_expr(bond.expr, family)
        return
    if isinstance(expr, UnboundHybridization):
        if family != "xsmarts":
            raise WriteError(
                f"unbound hybridization ^{'' if expr.digit is None else expr.digit} "
                f"cannot be written for family={family!r}; call "
                "QueryMol.bind_hybridization(source_dialect) first"
            )
        return
    if family == "xsmarts":
        # The superset spells every primitive except bound hybridization
        # kinds that no single digit means in every dialect.
        if isinstance(expr, Hybridization):
            from .dialect import consistent_digits

            if expr.kind not in consistent_digits().values():
                raise WriteError(
                    f"hybridization {expr.kind!r} has no dialect-independent ^n "
                    "spelling; write to a concrete dialect"
                )
        return
    if isinstance(expr, _RDKIT_ONLY) and family != "rdkit":
        raise WriteError(
            f"{type(expr).__name__} is RDKit-only and cannot be written for "
            f"family={family!r}"
        )
    if isinstance(expr, _RDKIT_OR_CHEMATIC) and family not in ("rdkit", "chematic"):
        raise WriteError(
            f"{type(expr).__name__} requires family 'rdkit' or 'chematic', "
            f"not {family!r}"
        )
    if isinstance(expr, _CDK_ONLY) and family != "cdk":
        raise WriteError(
            f"{type(expr).__name__} is CDK-only and cannot be written for "
            f"family={family!r}"
        )
    if isinstance(expr, Insaturation) and family != "cdk" and not emulate_extensions:
        raise WriteError(
            "Insaturation (i/iN) is CDK-only; pass emulate_extensions=True to "
            f"emit recursive SMARTS for family={family!r}"
        )
    if isinstance(expr, Hybridization):
        if family == "opensmarts":
            raise WriteError(
                "Hybridization (^n) is not part of OpenSMARTS; "
                "use family 'rdkit', 'cdk', 'chematic', or 'openbabel'"
            )
        from .hyb import kind_to_digit

        try:
            kind_to_digit(family, expr.kind)
        except ValueError as e:
            raise WriteError(str(e)) from e
    if _has_range(expr) and family in ("opensmarts", "chematic", "openbabel"):
        raise WriteError(
            f"count ranges {{lo-hi}} require family 'rdkit' or 'cdk', "
            f"not {family!r} ({type(expr).__name__})"
        )


def _has_range(expr: AtomExpr) -> bool:
    for attr in ("count",):
        c = getattr(expr, attr, None)
        if isinstance(c, Count) and c.range is not None:
            return True
    return False


def _validate_bond_expr(expr: BondExpr, family: Family) -> None:
    if isinstance(expr, BondNot):
        _validate_bond_expr(expr.expr, family)
        return
    if isinstance(expr, (BondAnd, BondOr)):
        for p in expr.parts:
            _validate_bond_expr(p, family)
        return
    if isinstance(expr, (DativeRight, DativeLeft)) and family not in ("rdkit", "cdk", "xsmarts"):
        raise WriteError(
            f"dative bonds (-> / <-) require family 'rdkit' or 'cdk', not {family!r}"
        )


def _components(mol: QueryMol) -> list[list[int]]:
    if mol.atom_component:
        by: dict[int, list[int]] = {}
        for i, c in enumerate(mol.atom_component):
            by.setdefault(c, []).append(i)
        return [by[k] for k in sorted(by)]
    n = mol.n_atoms
    adj: list[list[int]] = [[] for _ in range(n)]
    for b in mol.bonds:
        adj[b.a].append(b.b)
        adj[b.b].append(b.a)
    seen = [False] * n
    out: list[list[int]] = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        comp: list[int] = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        out.append(sorted(comp))
    return out


def _write_reaction(
    mol: QueryMol,
    family: Family,
    *,
    emulate_extensions: bool = False,
) -> str:
    by_role: dict[Role, list[int]] = {"reactant": [], "agent": [], "product": []}
    for i, role in enumerate(mol.atom_role):
        by_role[role].append(i)

    def role_smarts(indices: list[int]) -> str:
        if not indices:
            return ""
        return write_smarts(
            _subgraph(mol, indices),
            family,
            emulate_extensions=emulate_extensions,
        )

    r = role_smarts(by_role["reactant"])
    a = role_smarts(by_role["agent"])
    p = role_smarts(by_role["product"])
    if not any(role != "reactant" for role in mol.atom_role):
        return r
    return f"{r}>{a}>{p}"


def _subgraph(mol: QueryMol, indices: list[int]) -> QueryMol:
    imap = {old: new for new, old in enumerate(indices)}
    atoms = tuple(mol.atoms[i] for i in indices)
    bonds = tuple(
        type(b)(imap[b.a], imap[b.b], b.expr)
        for b in mol.bonds
        if b.a in imap and b.b in imap
    )
    if mol.atom_component:
        raw = [mol.atom_component[i] for i in indices]
        uniq = {c: n for n, c in enumerate(sorted(set(raw)))}
        comp = tuple(uniq[c] for c in raw)
    else:
        comp = ()
    return QueryMol(atoms=atoms, bonds=bonds, atom_component=comp, atom_role=())


def _write_component(
    mol: QueryMol,
    atom_indices: list[int],
    family: Family,
    *,
    emulate_extensions: bool = False,
) -> str:
    sub = (
        _subgraph(mol, atom_indices)
        if atom_indices != list(range(mol.n_atoms))
        else mol
    )
    if sub.n_atoms == 0:
        return ""
    return _SmilesWriter(
        sub, family, emulate_extensions=emulate_extensions
    ).write()


class _SmilesWriter:
    def __init__(
        self,
        mol: QueryMol,
        family: Family,
        *,
        emulate_extensions: bool = False,
    ):
        self.mol = mol
        self.family = family
        self.emulate_extensions = emulate_extensions
        self.adj: list[list[tuple[int, BondExpr]]] = [[] for _ in range(mol.n_atoms)]
        for b in mol.bonds:
            self.adj[b.a].append((b.b, b.expr))
            self.adj[b.b].append((b.a, b.expr))
        self.visited: set[int] = set()
        self._tree: dict[int, list[tuple[int, BondExpr]]] = {
            i: [] for i in range(mol.n_atoms)
        }
        self._rings_at: list[list[tuple[int, BondExpr]]] = [
            [] for _ in range(mol.n_atoms)
        ]
        self._has_parent: set[int] = set()

    def write(self) -> str:
        for atom in self.mol.atoms:
            _validate_atom_expr(
                atom.expr, self.family, emulate_extensions=self.emulate_extensions
            )
        for bond in self.mol.bonds:
            _validate_bond_expr(bond.expr, self.family)
        self._assign_rings()
        roots = [i for i in range(self.mol.n_atoms) if i not in self._has_parent]
        if not roots:
            roots = [0]
        return self._dfs(roots[0], bond_from_parent=None, parent=None)

    def _assign_rings(self) -> None:
        seen: set[int] = set()
        back: list[tuple[int, int, BondExpr]] = []

        def walk(u: int, parent: int | None) -> None:
            seen.add(u)
            for v, expr in self.adj[u]:
                if v == parent:
                    continue
                if v not in seen:
                    self._has_parent.add(v)
                    self._tree[u].append((v, expr))
                    walk(v, u)
                else:
                    a, b = (u, v) if u < v else (v, u)
                    if not any(x == a and y == b for x, y, _ in back):
                        back.append((a, b, expr))

        for i in range(self.mol.n_atoms):
            if i not in seen:
                walk(i, None)

        for rid, (a, b, expr) in enumerate(back, start=1):
            self._rings_at[a].append((rid, expr))
            self._rings_at[b].append((rid, expr))

    def _dfs(
        self,
        u: int,
        bond_from_parent: BondExpr | None,
        parent: int | None,
    ) -> str:
        self.visited.add(u)
        parts: list[str] = []
        force_bracket = False
        if bond_from_parent is not None:
            bs = _bond_to_smarts(bond_from_parent, self.family)
            # Omitted bond + ``C``+``n`` → ``Cn``. Bracket the child instead of
            # emitting ``-`` (which would change SingleOrAromatic → Single).
            if (
                bs == ""
                and parent is not None
                and _omitted_bond_glues(
                    self.mol.atoms[parent].expr,
                    _as_organic(self.mol.atoms[u].expr) or "",
                )
            ):
                force_bracket = True
            parts: list[str] = [bs]
        else:
            parts = []
        atom_s = _atom_to_smarts(
            self.mol.atoms[u].expr,
            self.family,
            emulate_extensions=self.emulate_extensions,
            force_bracket=force_bracket,
            mapno=self.mol.atoms[u].mapno,
        )
        parts.append(atom_s)
        for rid, expr in self._rings_at[u]:
            parts.append(_bond_to_smarts(expr, self.family) + _ring_tag(rid))

        children = sorted(
            ((v, e) for v, e in self._tree[u] if v not in self.visited),
            key=lambda ve: ve[0],
        )
        if not children:
            return "".join(parts)
        *branches, main = children
        for v, e in branches:
            parts.append("(" + self._dfs(v, e, parent=u) + ")")
        parts.append(self._dfs(main[0], main[1], parent=u))
        return "".join(parts)


def _omitted_bond_glues(parent_expr: AtomExpr, child_organic: str) -> bool:
    """True if omitted bond would merge aliphatic + aromatic into one element."""
    if not child_organic or child_organic[0] == "[" or not child_organic[0].islower():
        return False
    parent_org = _as_organic(parent_expr)
    return bool(parent_org and parent_org[0].isupper())


def _ring_tag(rid: int) -> str:
    return str(rid) if rid < 10 else f"%{rid:02d}"


def _chirality_to_smarts(c: Chirality) -> str:
    suffix = "?" if c.or_unspecified else ""
    if c.class_ is not None:
        code = {
            "tetrahedral": "TH",
            "allene": "AL",
            "square_planar": "SP",
            "trigonal_bipyramidal": "TB",
            "octahedral": "OH",
        }[c.class_]
        if c.permutation is None and c.or_unspecified:
            return f"@{code}?"
        perm = "" if c.permutation is None else str(c.permutation)
        return f"@{code}{perm}{suffix}"
    if c.clockwise:
        return "@@" + suffix
    return "@" + suffix


def _atom_to_smarts(
    expr: AtomExpr,
    family: Family,
    *,
    emulate_extensions: bool = False,
    force_bracket: bool = False,
    mapno: int | None = None,
) -> str:
    # Mapped atoms must be bracketed (``[C:1]``, not ``C:1``).
    if mapno is not None:
        force_bracket = True
    organic = None if force_bracket else _as_organic(expr)
    if organic is not None:
        return organic
    body = _atom_expr_to_smarts(
        expr, "low", family, emulate_extensions=emulate_extensions
    )
    # ``:n`` comes from QueryAtom.mapno only — not from match expr.
    if mapno is not None:
        body = f"{body}:{mapno}"
    return "[" + body + "]"


def _as_organic(expr: AtomExpr) -> str | None:
    if isinstance(expr, AnyAtom):
        return "*"
    if isinstance(expr, Element) and expr.symbol in _ORGANIC:
        if expr.aromatic is True and expr.symbol.islower():
            return expr.symbol
        if expr.aromatic is False and expr.symbol in {
            "B",
            "C",
            "N",
            "O",
            "S",
            "P",
            "F",
            "Cl",
            "Br",
            "I",
        }:
            return expr.symbol
        if expr.aromatic is None and expr.symbol in _ORGANIC:
            return expr.symbol
    return None


def _is_identity_primitive(expr: AtomExpr) -> bool:
    return isinstance(
        expr, (Element, AtomicNumber, AnyAtom, Aromatic, Aliphatic, HeteroAny)
    )


def _write_order_and_parts(parts: tuple[AtomExpr, ...]) -> list[AtomExpr]:
    """Isotope → identity → other → map (terse Daylight-ish bracket order)."""
    maps = [p for p in parts if isinstance(p, AtomMap)]
    rest = [p for p in parts if not isinstance(p, AtomMap)]
    isotopes = [p for p in rest if isinstance(p, Isotope)]
    identity = [p for p in rest if _is_identity_primitive(p)]
    other = [p for p in rest if not isinstance(p, Isotope) and not _is_identity_primitive(p)]
    return isotopes + identity + other + maps


def _can_juxtapose(left: str, right: str) -> bool:
    """True only for glues that are unambiguous; otherwise prefer ``;`` / ``&``.

    Conservative on purpose — terse ``CH2`` / ``CX4`` forms are nice but easy
    to get wrong (``A``+``r`` → ``Ar``, ``N``+``i`` → ``Ni``, …). Disabled
    entirely when :data:`_ALLOW_JUXTAPOSE` is False (round-trip fallback).
    """
    if not _ALLOW_JUXTAPOSE.get():
        return False
    if not left or not right:
        return False
    # Never glue across OR/AND expressions.
    if any(c in left for c in ",;&") and right[0] != ":":
        return False
    if any(c in right for c in ",;&"):
        return False
    # Atom map, chirality, charge, hybridization.
    if right[0] in ":@+-^":
        return True
    # Isotope digits then symbol / #n (``12C``, ``12#6``).
    if left.isdigit() and (right[0].isalpha() or right.startswith("#")):
        return True
    return False


def _join_atom_and_parts(
    parts: list[AtomExpr],
    prec: str,
    family: Family,
    *,
    emulate_extensions: bool,
) -> str:
    """Join AND children: juxtapose when safe, else ``;`` / ``&``; maps as ``:n``."""
    if not parts:
        return "*"
    sep = "&" if prec in {"or", "and", "not"} else ";"
    child_prec = "and" if sep == "&" else "low"
    ordered = _write_order_and_parts(tuple(parts))
    body: list[AtomExpr] = [p for p in ordered if not isinstance(p, AtomMap)]
    maps = [p for p in ordered if isinstance(p, AtomMap)]
    if not body:
        # Map-only atom — still legal as ``[:1]`` in some toolkits; emit ``*:n``.
        out = "*"
    else:
        rendered = [
            _atom_expr_to_smarts(
                p, child_prec, family, emulate_extensions=emulate_extensions
            )
            for p in body
        ]
        out = rendered[0]
        for piece in rendered[1:]:
            if _can_juxtapose(out, piece):
                out += piece
            else:
                out += sep + piece
    for m in maps:
        out += f":{m.n}"
    return out


def _atom_expr_to_smarts(
    expr: AtomExpr,
    prec: str,
    family: Family,
    *,
    emulate_extensions: bool = False,
) -> str:
    if isinstance(expr, AtomNot):
        return "!" + _atom_expr_to_smarts(
            expr.expr, "not", family, emulate_extensions=emulate_extensions
        )
    if isinstance(expr, AtomOr):
        s = ",".join(
            _atom_expr_to_smarts(p, "or", family, emulate_extensions=emulate_extensions)
            for p in expr.parts
        )
        return s if prec in {"low", "or"} else f"({s})"
    if isinstance(expr, AtomAnd):
        return _join_atom_and_parts(
            list(expr.parts),
            prec,
            family,
            emulate_extensions=emulate_extensions,
        )

    if isinstance(expr, Recursive):
        return "$(%s)" % write_smarts(
            expr.mol, family, emulate_extensions=emulate_extensions
        )
    if isinstance(expr, AnyAtom):
        return "*"
    if isinstance(expr, Element):
        return expr.symbol
    if isinstance(expr, AtomicNumber):
        return f"#{expr.n}"
    if isinstance(expr, Isotope):
        return str(expr.mass)
    if isinstance(expr, AtomMap):
        return f":{expr.n}"
    if isinstance(expr, Charge):
        if expr.value == 1:
            return "+"
        if expr.value == -1:
            return "-"
        if expr.value == 2:
            return "++"
        if expr.value == -2:
            return "--"
        return f"+{expr.value}" if expr.value > 0 else str(expr.value)
    if isinstance(expr, Aromatic):
        return "a"
    if isinstance(expr, Aliphatic):
        return "A"
    if isinstance(expr, Chirality):
        return _chirality_to_smarts(expr)
    if isinstance(expr, UnboundHybridization):
        return "^" if expr.digit is None else f"^{expr.digit}"
    if isinstance(expr, Hybridization):
        if family == "xsmarts":
            from .dialect import consistent_digits

            digit = {k: d for d, k in consistent_digits().items()}[expr.kind]
            return f"^{digit}"
        from .hyb import kind_to_digit

        return f"^{kind_to_digit(family, expr.kind)}"
    if isinstance(expr, HeteroAny):
        return "#X"
    if isinstance(expr, PeriodicGroup):
        return f"#G{expr.n}" if expr.hashed else f"G{expr.n}"
    if isinstance(expr, Degree):
        return "D" + _count_suffix(expr.count)
    if isinstance(expr, Valence):
        return "v" + _count_suffix(expr.count)
    if isinstance(expr, Connectivity):
        return "X" + _count_suffix(expr.count)
    if isinstance(expr, TotalH):
        # Prefer ``H1`` over bare ``H`` so reparse cannot become element H
        # when TotalH is the only identity (e.g. ``[H1:1]``).
        if (
            expr.count.value == 1
            and expr.count.range is None
            and not expr.count.defaulted
        ):
            return "H1"
        return "H" + _count_suffix(expr.count)
    if isinstance(expr, ImplicitH):
        # Bare ``h`` only for toolkit-defaulted; ``h1`` is exact count 1.
        if expr.count.defaulted:
            return "h"
        if (
            expr.count.value == 1
            and expr.count.range is None
        ):
            return "h1"
        return "h" + _count_suffix(expr.count)
    if isinstance(expr, RingMembership):
        return "R" + _count_suffix(expr.count)
    if isinstance(expr, RingSize):
        return "r" + _count_suffix(expr.count)
    if isinstance(expr, RingConnectivity):
        return "x" + _count_suffix(expr.count)
    if isinstance(expr, HeteroNeighbors):
        return "z" + _count_suffix(expr.count)
    if isinstance(expr, AliphaticHeteroNeighbors):
        return "Z" + _count_suffix(expr.count)
    if isinstance(expr, NonHDegree):
        return "d" + _count_suffix(expr.count)
    if isinstance(expr, RingSizeK):
        return "k" + _count_suffix(expr.count)
    if isinstance(expr, Insaturation):
        if family in ("cdk", "xsmarts"):
            return "i" + _count_suffix(expr.count)
        if not emulate_extensions:
            raise WriteError(
                "Insaturation (i/iN) is CDK-only; pass emulate_extensions=True "
                f"to emit recursive SMARTS for family={family!r}"
            )
        from .insat_patterns import insat_smarts_open

        return insat_smarts_open(expr)
    raise TypeError(f"unknown atom expr {type(expr)}: {expr!r}")


def _count_suffix(count: Count) -> str:
    if count.range is not None:
        return _range_to_smarts(count.range)
    if count.defaulted:
        return ""
    assert count.value is not None
    return str(count.value)


def _range_to_smarts(rng: IntRange) -> str:
    if rng.min is not None and rng.max is not None:
        return f"{{{rng.min}-{rng.max}}}"
    if rng.min is not None:
        return f"{{{rng.min}-}}"
    assert rng.max is not None
    return f"{{-{rng.max}}}"


def _bond_to_smarts(expr: BondExpr, family: Family = "opensmarts") -> str:
    if isinstance(expr, SingleOrAromatic):
        return ""
    if isinstance(expr, BondNot):
        return "!" + _bond_to_smarts(expr.expr, family)
    if isinstance(expr, BondOr):
        return ",".join(_bond_to_smarts(p, family) or "-" for p in expr.parts)
    if isinstance(expr, BondAnd):
        if expr.tight:
            return "".join(_bond_to_smarts(p, family) or "-" for p in expr.parts)
        return ";".join(_bond_to_smarts(p, family) or "-" for p in expr.parts)
    return {
        SingleBond: "-",
        DoubleBond: "=",
        TripleBond: "#",
        QuadrupleBond: "$",
        AromaticBond: ":",
        AnyBond: "~",
        RingBond: "@",
        UpBond: "/",
        DownBond: "\\",
        UpOrUnspec: "/?",
        DownOrUnspec: "\\?",
        DativeRight: "->",
        DativeLeft: "<-",
    }[type(expr)]
