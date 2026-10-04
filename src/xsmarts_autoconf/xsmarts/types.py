"""Typed QueryMol graph and atom/bond query expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

Role = Literal["reactant", "agent", "product"]


# ----- numeric helpers -----


@dataclass(frozen=True, slots=True)
class IntRange:
    """Inclusive range; open ends use None (e.g. {2-} → min=2, max=None)."""

    min: int | None = None
    max: int | None = None

    def __post_init__(self) -> None:
        if self.min is None and self.max is None:
            raise ValueError("IntRange needs at least one bound")


@dataclass(frozen=True, slots=True)
class Count:
    """Exact count, or a range (RDKit/CDK ``{..}`` extensions)."""

    value: int | None = None
    range: IntRange | None = None
    defaulted: bool = False  # True when SMARTS omitted the number (toolkit default)

    def __post_init__(self) -> None:
        if self.value is None and self.range is None and not self.defaulted:
            raise ValueError("Count needs value, range, or defaulted=True")


# ----- atom primitives -----


@dataclass(frozen=True, slots=True)
class AnyAtom:
    """``*`` — wildcard atom (also marked dummy on the graph node)."""


@dataclass(frozen=True, slots=True)
class Element:
    """Element symbol; ``aromatic`` True/False for a/c vs A/C style, None if unspecified."""

    symbol: str
    aromatic: bool | None = None


@dataclass(frozen=True, slots=True)
class AtomicNumber:
    n: int


@dataclass(frozen=True, slots=True)
class Isotope:
    mass: int


@dataclass(frozen=True, slots=True)
class AtomMap:
    """Legacy leaf for SMARTS ``:n``. Prefer :attr:`QueryAtom.mapno`.

    The parser never places this in :attr:`QueryAtom.expr`; it exists only so
    hand-built IR / canonicalize can still hoist stray map leaves.
    """

    n: int


@dataclass(frozen=True, slots=True)
class Charge:
    value: int


@dataclass(frozen=True, slots=True)
class Aromatic:
    """``a`` — any aromatic atom."""


@dataclass(frozen=True, slots=True)
class Aliphatic:
    """``A`` — any aliphatic atom."""


@dataclass(frozen=True, slots=True)
class Degree:
    """``D`` — explicit degree."""

    count: Count


@dataclass(frozen=True, slots=True)
class Valence:
    """``v`` — total valence."""

    count: Count


@dataclass(frozen=True, slots=True)
class Connectivity:
    """``X`` — total connections."""

    count: Count


@dataclass(frozen=True, slots=True)
class TotalH:
    """``H`` — total hydrogen count."""

    count: Count


@dataclass(frozen=True, slots=True)
class ImplicitH:
    """``h`` — implicit hydrogen count."""

    count: Count


@dataclass(frozen=True, slots=True)
class RingMembership:
    """``R`` — number of SSSR rings."""

    count: Count


@dataclass(frozen=True, slots=True)
class RingSize:
    """``r`` — size of smallest ring."""

    count: Count


@dataclass(frozen=True, slots=True)
class RingConnectivity:
    """``x`` — number of ring bonds."""

    count: Count


@dataclass(frozen=True, slots=True)
class Chirality:
    """Tetrahedral / extended stereo constraint (not the raw ``@…`` token)."""

    clockwise: bool | None = None
    """False for ``@``, True for ``@@``; None when a chiral class is used."""
    class_: Literal[
        "tetrahedral",
        "allene",
        "square_planar",
        "trigonal_bipyramidal",
        "octahedral",
    ] | None = None
    permutation: int | None = None
    or_unspecified: bool = False
    """True for ``@?`` / class``?`` — match either stereo or unspecified."""


@dataclass(frozen=True, slots=True)
class Hybridization:
    """Canonical hybridization kind (shared meaning across dialects).

    Parse maps dialect ``^n`` → kind; write maps kind → ``^n`` or raises if
    the target family has no slot. See ``hyb.DIGIT_TO_KIND``.
    """

    kind: str  # HybKind — kept as str for forward-compat / pickle simplicity


@dataclass(frozen=True, slots=True)
class UnboundHybridization:
    """XSMARTS ``^n`` (or bare ``^``) whose meaning depends on the dialect.

    Digits whose meaning differs between dialects (see ``hyb.py`` and
    docs/smarts_dialects.md) are kept as written by the XSMARTS parser;
    :meth:`QueryMol.bind_hybridization` turns them into :class:`Hybridization`.
    """

    digit: int | None  # None = bare ``^``


@dataclass(frozen=True, slots=True)
class HeteroNeighbors:
    """RDKit ``z`` — heteroatom neighbor count."""

    count: Count


@dataclass(frozen=True, slots=True)
class AliphaticHeteroNeighbors:
    """RDKit ``Z``."""

    count: Count


@dataclass(frozen=True, slots=True)
class NonHDegree:
    """RDKit ``d`` — non-hydrogen degree."""

    count: Count


@dataclass(frozen=True, slots=True)
class RingSizeK:
    """RDKit ``k`` — atom in a ring of size count."""

    count: Count


@dataclass(frozen=True, slots=True)
class HeteroAny:
    """CDK/MOE ``#X`` — any non-carbon heavy atom."""


@dataclass(frozen=True, slots=True)
class PeriodicGroup:
    """CDK/MOE ``G`` / ``#G``."""

    n: int
    hashed: bool = False


@dataclass(frozen=True, slots=True)
class Insaturation:
    """CDK/CACTVS ``i``."""

    count: Count


@dataclass(frozen=True, slots=True)
class Recursive:
    """Recursive SMARTS: atom matches if ``mol`` matches with ``anchor`` coinciding."""

    mol: QueryMol
    anchor: int = 0


AtomPrimitive = Union[
    AnyAtom,
    Element,
    AtomicNumber,
    Isotope,
    AtomMap,
    Charge,
    Aromatic,
    Aliphatic,
    Degree,
    Valence,
    Connectivity,
    TotalH,
    ImplicitH,
    RingMembership,
    RingSize,
    RingConnectivity,
    Chirality,
    Hybridization,
    UnboundHybridization,
    HeteroNeighbors,
    AliphaticHeteroNeighbors,
    NonHDegree,
    RingSizeK,
    HeteroAny,
    PeriodicGroup,
    Insaturation,
    Recursive,
]


@dataclass(frozen=True, slots=True)
class AtomNot:
    expr: AtomExpr


@dataclass(frozen=True, slots=True)
class AtomAnd:
    """High-and (``&`` or juxtaposition) when ``tight`` else low-and (``;``)."""

    parts: tuple[AtomExpr, ...]
    tight: bool = True


@dataclass(frozen=True, slots=True)
class AtomOr:
    parts: tuple[AtomExpr, ...]


AtomExpr = Union[AtomPrimitive, AtomNot, AtomAnd, AtomOr]


# ----- bond primitives -----


@dataclass(frozen=True, slots=True)
class SingleBond:
    pass


@dataclass(frozen=True, slots=True)
class DoubleBond:
    pass


@dataclass(frozen=True, slots=True)
class TripleBond:
    pass


@dataclass(frozen=True, slots=True)
class QuadrupleBond:
    pass


@dataclass(frozen=True, slots=True)
class AromaticBond:
    pass


@dataclass(frozen=True, slots=True)
class AnyBond:
    """``~``."""


@dataclass(frozen=True, slots=True)
class RingBond:
    """``@`` — bond is in a ring."""


@dataclass(frozen=True, slots=True)
class SingleOrAromatic:
    """Omitted bond in SMARTS — single or aromatic."""


@dataclass(frozen=True, slots=True)
class UpBond:
    """``/``."""


@dataclass(frozen=True, slots=True)
class DownBond:
    """``\\``."""


@dataclass(frozen=True, slots=True)
class UpOrUnspec:
    """``/?``."""


@dataclass(frozen=True, slots=True)
class DownOrUnspec:
    """``\\?``."""


@dataclass(frozen=True, slots=True)
class DativeRight:
    """``->``."""


@dataclass(frozen=True, slots=True)
class DativeLeft:
    """``<-``."""


BondPrimitive = Union[
    SingleBond,
    DoubleBond,
    TripleBond,
    QuadrupleBond,
    AromaticBond,
    AnyBond,
    RingBond,
    SingleOrAromatic,
    UpBond,
    DownBond,
    UpOrUnspec,
    DownOrUnspec,
    DativeRight,
    DativeLeft,
]


@dataclass(frozen=True, slots=True)
class BondNot:
    expr: BondExpr


@dataclass(frozen=True, slots=True)
class BondAnd:
    parts: tuple[BondExpr, ...]
    tight: bool = True


@dataclass(frozen=True, slots=True)
class BondOr:
    parts: tuple[BondExpr, ...]


BondExpr = Union[BondPrimitive, BondNot, BondAnd, BondOr]


# ----- graph -----


@dataclass(frozen=True, slots=True)
class QueryAtom:
    """Node in a QueryMol graph."""

    expr: AtomExpr
    dummy: bool = False
    """True for ``*`` / attachment placeholders; bonds may connect here."""
    mapno: int | None = None
    """Atom-map number (``:n``). Tracking only — not part of match ``expr``."""


@dataclass(frozen=True, slots=True)
class QueryBond:
    """Edge in a QueryMol graph; ``a``/``b`` are atom indices (either may be dummy)."""

    a: int
    b: int
    expr: BondExpr = field(default_factory=SingleOrAromatic)


@dataclass(frozen=True, slots=True)
class OpenRing:
    """A ring-closure digit opened on ``atom`` and never closed.

    Parsers record these instead of failing; validators decide what to do
    (error, warn, ignore, or close against another atom).
    """

    ring_id: str
    """Digits as written, without ``%`` (``"1"``, ``"12"``)."""
    atom: int
    bond: BondExpr = field(default_factory=SingleOrAromatic)


@dataclass(frozen=True, slots=True)
class QueryMol:
    """
    Query molecule as an undirected graph.

    ``atoms`` / ``bonds`` are in SMARTS serial order (ring-closure bonds are
    recorded when the closing digit is seen). Nodes may be dummies; edges may
    attach to dummies. Atom/bond ``expr`` payloads are typed *match
    constraints* only — atom maps live on :attr:`QueryAtom.mapno`.
    """

    atoms: tuple[QueryAtom, ...]
    bonds: tuple[QueryBond, ...] = ()
    atom_component: tuple[int, ...] = ()
    """Component id per atom (``.`` separation within a role)."""
    atom_role: tuple[Role, ...] = ()
    """Reaction role per atom; empty if not a reaction query."""
    open_rings: tuple[OpenRing, ...] = ()
    """Ring closures opened but never closed, in opening order."""

    def __post_init__(self) -> None:
        n = len(self.atoms)
        if self.atom_component and len(self.atom_component) != n:
            raise ValueError("atom_component length must match atoms")
        if self.atom_role and len(self.atom_role) != n:
            raise ValueError("atom_role length must match atoms")
        for b in self.bonds:
            if not (0 <= b.a < n and 0 <= b.b < n):
                raise ValueError(f"bond endpoints out of range: {b}")
        for r in self.open_rings:
            if not 0 <= r.atom < n:
                raise ValueError(f"open ring atom out of range: {r}")

    def atom_mapnos(self) -> tuple[int | None, ...]:
        """Per-atom map numbers (``None`` if unmapped)."""
        return tuple(a.mapno for a in self.atoms)

    @property
    def n_atoms(self) -> int:
        return len(self.atoms)

    @property
    def n_bonds(self) -> int:
        return len(self.bonds)

    def neighbors(self, idx: int) -> tuple[tuple[int, QueryBond], ...]:
        out: list[tuple[int, QueryBond]] = []
        for b in self.bonds:
            if b.a == idx:
                out.append((b.b, b))
            elif b.b == idx:
                out.append((b.a, b))
        return tuple(out)

    # ----- dialects (implemented in dialect.py; local imports avoid cycles)

    def unbound_hybridization(self) -> tuple[int | None, ...]:
        """Unbound ``^n`` digits in this query (recursive SMARTS included)."""
        from .dialect import unbound_hybridization

        return unbound_hybridization(self)

    def bind_hybridization(self, dialect: str) -> "QueryMol":
        """Bind XSMARTS ``^n`` digits using ``dialect``'s meaning.

        Returns a canonical, dialect-independent QueryMol. Raises
        :class:`~smarts_grammar.dialect.BindError` if a digit has no meaning
        in ``dialect`` (e.g. ``^6`` for RDKit, bare ``^`` outside Open Babel).
        """
        from .dialect import bind_hybridization

        return bind_hybridization(self, dialect)

    def dialect_issues(self, dialect: str, *, emulate_extensions: bool = False) -> list[str]:
        """Reasons this query cannot be written in ``dialect`` (empty if it can)."""
        from .dialect import dialect_issues

        return dialect_issues(self, dialect, emulate_extensions=emulate_extensions)

    def expressible_in(self, dialect: str, *, emulate_extensions: bool = False) -> bool:
        return not self.dialect_issues(dialect, emulate_extensions=emulate_extensions)

    def to_smarts(self, dialect: str = "xsmarts", *, emulate_extensions: bool = False) -> str:
        """Write as ``dialect`` SMARTS/SMIRKS (default: the XSMARTS superset)."""
        from .write import write_smarts

        return write_smarts(self, dialect, emulate_extensions=emulate_extensions)  # type: ignore[arg-type]

