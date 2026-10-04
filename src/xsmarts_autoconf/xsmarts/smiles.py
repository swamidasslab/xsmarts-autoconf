"""SMILES → SmilesMol: what was written, with no perception or validation.

``parse_smiles(s)`` uses ``grammars/smiles.lark`` and records:

- atoms as written: symbol (``c`` stays lowercase), bracket or organic
  subset (``hcount`` is ``None`` for organic-subset atoms: implicit H is
  perceived later), isotope, chirality token, charge, atom class;
- bonds as written: the symbol between the atoms (``None`` if none was
  written) and, for ring closures, the label and the symbol written at
  each end;
- the written neighbour order around each stereocentre (needed to read
  ``@``/``@@``), with ``None`` for a ring partner that never closed;
- ring closures that were opened and never closed.

SMILES conventions (an unwritten bond between aromatic atoms is aromatic,
``<-`` reverses the dative direction, ``/``/``\\`` flip at a closing ring
digit) and all chemistry are applied later — in Rust by
``SmilesMol::to_chematic`` — so parsing never branches on chemistry.
This module is the Python reference for the generated Rust parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lark import Lark, Token, Tree

_GRAMMAR = Path(__file__).resolve().parent / "grammars" / "smiles.lark"


@dataclass(frozen=True, slots=True)
class SmilesAtom:
    symbol: str
    """As written: ``C``, ``c``, ``Cl``, ``se``, ``*``."""
    bracket: bool
    isotope: int | None = None
    chirality: str | None = None
    """Token as written: ``@``, ``@@``, ``@SP1``, ``@TH2`` …"""
    hcount: int | None = None
    """Bracket H count (0 if none written); ``None`` for organic subset."""
    charge: int = 0
    atom_class: int | None = None


@dataclass(frozen=True, slots=True)
class SmilesBond:
    a: int
    b: int
    symbol: str | None
    """Symbol as written (``None`` = none written). Ring bonds: opening end."""
    ring: int | None = None
    """Ring number for ring-closure bonds (``1``, ``%12`` → 12, ``%(123)``)."""
    close_symbol: str | None = None
    """Ring bonds: symbol written at the closing digit (read close→open)."""


@dataclass(frozen=True, slots=True)
class StereoOrder:
    atom: int
    has_from: bool
    """True if ``neighbors[0]`` is the atom this one was written after."""
    neighbors: tuple[int | None, ...]
    """Neighbours in written order; ``None`` = ring partner never closed."""


@dataclass(frozen=True, slots=True)
class OpenSmilesRing:
    ring: int
    atom: int
    symbol: str | None


@dataclass(frozen=True, slots=True)
class SmilesMol:
    atoms: tuple[SmilesAtom, ...]
    bonds: tuple[SmilesBond, ...]
    component: tuple[int, ...]
    stereo: tuple[StereoOrder, ...] = ()
    open_rings: tuple[OpenSmilesRing, ...] = field(default=())
    atom_labels: tuple[str | None, ...] = ()
    """CXSMILES ``$...$`` labels in written atom order (``None`` = empty)."""
    cx_fields: tuple[str, ...] = ()
    """Other CXSMILES fields, raw."""


@lru_cache(maxsize=1)
def _parser() -> Lark:
    return Lark.open(str(_GRAMMAR), parser="lalr", maybe_placeholders=False)


def parse_smiles(smiles: str) -> SmilesMol:
    return _Builder().build(_parser().parse(smiles))


def _charge(text: str) -> int:
    if text in ("++", "--"):
        return 2 if text == "++" else -2
    sign = 1 if text[0] == "+" else -1
    return sign * (int(text[1:]) if len(text) > 1 else 1)


class _Builder:
    def __init__(self) -> None:
        self.atoms: list[SmilesAtom] = []
        self.component: list[int] = []
        self.bonds: list[SmilesBond] = []
        self.prev: int | None = None
        self.comp = -1
        # label -> (atom, symbol, slot); slot indexes self.pending
        self.rings: dict[int, tuple[int, str | None, int]] = {}
        self.atom_labels: tuple[str | None, ...] = ()
        self.cx_fields: tuple[str, ...] = ()
        self.pending: list[tuple[int, int] | None] = []  # slot -> (atom, position)
        self.order: dict[int, list[int | None]] = {}
        self.has_from: dict[int, bool] = {}

    def build(self, tree: Tree) -> SmilesMol:
        if len(tree.children) > 1:  # CX_TRAILER
            self._cx(str(tree.children[1]))
        for mol in tree.children[0].children:  # start -> smiles -> mol*
            self.comp += 1
            self.prev = None
            self._walk(mol.children)
        stereo = tuple(
            StereoOrder(a, self.has_from[a], tuple(nb)) for a, nb in self.order.items()
        )
        open_rings = tuple(OpenSmilesRing(r, a, s) for r, (a, s, _) in self.rings.items())
        return SmilesMol(
            tuple(self.atoms), tuple(self.bonds), tuple(self.component), stereo, open_rings,
            self.atom_labels, self.cx_fields,
        )

    def _cx(self, trailer: str) -> None:
        """Split ``|f1,f2,...|`` at top-level commas (not inside $..$ or (..))."""
        body = trailer.strip()[1:-1]
        fields, cur, in_label, depth = [], "", False, 0
        for ch in body:
            if ch == "$":
                in_label = not in_label
            elif ch == "(" and not in_label:
                depth += 1
            elif ch == ")" and not in_label:
                depth -= 1
            if ch == "," and not in_label and depth == 0:
                fields.append(cur)
                cur = ""
            else:
                cur += ch
        if cur:
            fields.append(cur)
        rest = []
        for f in fields:
            if f.startswith("$") and f.endswith("$") and len(f) >= 2 and not self.atom_labels:
                self.atom_labels = tuple(x or None for x in f[1:-1].split(";"))
            else:
                rest.append(f)
        self.cx_fields = tuple(rest)

    def _walk(self, children) -> None:
        for c in children:
            name = c.data
            if name == "first_atom":
                self._add_atom(c.children[0], None)
            elif name == "chain":
                for ba in c.children:
                    self._bond_atom(ba)
            elif name == "branch":
                saved = self.prev
                self._walk([x for x in c.children if x.data not in ("open", "close")])
                self.prev = saved

    def _bond_atom(self, ba: Tree) -> None:
        symbol = None
        for c in ba.children:
            if c.data == "bond":
                symbol = str(c.children[0])
            elif c.data == "ring":
                self._ring(str(c.children[0]), symbol)
            else:
                self._add_atom(c, symbol)

    def _add_atom(self, atom: Tree, symbol: str | None) -> None:
        child = atom.children[0]
        if isinstance(child, Token):  # organic subset
            a = SmilesAtom(symbol=str(child), bracket=False)
        else:
            a = self._bracket(child)
        idx = len(self.atoms)
        self.atoms.append(a)
        self.component.append(self.comp)
        if a.chirality is not None:
            self.order[idx] = [] if self.prev is None else [self.prev]
            self.has_from[idx] = self.prev is not None
        if self.prev is not None:
            self.bonds.append(SmilesBond(self.prev, idx, symbol))
            if self.prev in self.order:
                self.order[self.prev].append(idx)
        self.prev = idx

    def _bracket(self, t: Tree) -> SmilesAtom:
        kw: dict = {"isotope": None, "chirality": None, "hcount": 0, "charge": 0, "atom_class": None}
        symbol = ""
        for c in t.children:
            if isinstance(c, Token):
                symbol = str(c)
            elif c.data == "isotope":
                kw["isotope"] = int(c.children[0])
            elif c.data == "chiral":
                kw["chirality"] = str(c.children[0])
            elif c.data == "hcount":
                text = str(c.children[0])
                kw["hcount"] = int(text[1:]) if len(text) > 1 else 1
            elif c.data == "charge":
                kw["charge"] = _charge(str(c.children[0]))
            elif c.data == "atom_class":
                kw["atom_class"] = int(c.children[0])
        return SmilesAtom(symbol=symbol, bracket=True, **kw)

    def _ring(self, text: str, symbol: str | None) -> None:
        label = int(text.lstrip("%").strip("()"))
        here = self.prev
        assert here is not None
        if label in self.rings:
            other, open_symbol, slot = self.rings.pop(label)
            self.bonds.append(SmilesBond(other, here, open_symbol, label, symbol))
            if here in self.order:
                self.order[here].append(other)
            if self.pending[slot] is not None:
                atom, pos = self.pending[slot]
                self.order[atom][pos] = here
        else:
            slot = len(self.pending)
            if here in self.order:
                self.pending.append((here, len(self.order[here])))
                self.order[here].append(None)
            else:
                self.pending.append(None)
            self.rings[label] = (here, symbol, slot)
