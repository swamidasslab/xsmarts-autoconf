"""Mol: the molecule graph the reference matcher and edit engine work on.

Plain data: atoms (element, charge, implicit H, aromatic flag, isotope) and
bonds (order, aromatic flag, ring flag), plus relevant-cycle rings. Derived per-atom
facts (degree, total H, valence, ring counts) are computed on demand and
cached; edits produce a new Mol (``Mol.edited``) so caches never go stale.

Perception is an input, not something Mol does. ``Mol.from_cdk`` takes the
facts CDK computed (``xenosmarts/harness/cdk_export.py``) so the matcher and
the edit engine can be checked against Ambit in isolation from aromaticity
and ring perception.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

_Z = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18, "K": 19,
    "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28,
    "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36, "Rb": 37,
    "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42, "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46,
    "Ag": 47, "Cd": 48, "In": 49, "Sn": 50, "Sb": 51, "Te": 52, "I": 53, "Xe": 54, "Cs": 55,
    "Ba": 56, "La": 57, "Pt": 78, "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82, "Bi": 83, "R": 0,
}

# Periodic group (CDK ``G``) for main-group elements.
_GROUP = {1: 1, 3: 1, 11: 1, 19: 1, 37: 1, 55: 1, 4: 2, 12: 2, 20: 2, 38: 2, 56: 2,
          5: 13, 13: 13, 31: 13, 49: 13, 81: 13, 6: 14, 14: 14, 32: 14, 50: 14, 82: 14,
          7: 15, 15: 15, 33: 15, 51: 15, 83: 15, 8: 16, 16: 16, 34: 16, 52: 16,
          9: 17, 17: 17, 35: 17, 53: 17, 2: 18, 10: 18, 18: 18, 36: 18, 54: 18}


def atomic_number(symbol: str) -> int:
    return _Z.get(symbol, 0)


@dataclass(frozen=True, slots=True)
class Atom:
    symbol: str
    charge: int = 0
    hcount: int = 0
    """Implicit H count (explicit H atoms are separate atoms)."""
    aromatic: bool = False
    isotope: int | None = None

    @property
    def z(self) -> int:
        return atomic_number(self.symbol)


@dataclass(frozen=True, slots=True)
class Bond:
    a: int
    b: int
    order: int  # 1, 2, 3, 4 (Kekulé orders; aromaticity is the flag)
    aromatic: bool = False
    ring: bool = False

    def other(self, i: int) -> int:
        return self.b if i == self.a else self.a


@dataclass(eq=False)
class Mol:
    atoms: list[Atom]
    bonds: list[Bond]
    dummies: frozenset[int] = frozenset()
    """Atoms Ambit could not re-type after an edit (written ``R``/``*``;
    AMBIT.md A25b). Only BioTransformer's validity check reads this."""
    rings: list[frozenset[int]] = field(default_factory=list)
    """Relevant cycles (union of all minimum cycle bases) as atom-index sets.

    Policy: not SSSR, which depends on atom order. Relevant cycles are unique
    and include every small ring; rare divergences from SSSR-based engines
    are accepted."""

    # ----- construction

    @classmethod
    def from_cdk(cls, d: dict) -> Mol:
        atoms = [Atom(a["symbol"], a["charge"], a["hcount"], a["aromatic"], a["isotope"]) for a in d["atoms"]]
        bonds = [Bond(b["a"], b["b"], b["order"], b["aromatic"], b["ring"]) for b in d["bonds"]]
        return cls(atoms, bonds, rings=[frozenset(r) for r in d["rings"]])

    # ----- derived facts (cached)

    @cached_property
    def adj(self) -> list[list[tuple[int, int]]]:
        """atom -> [(neighbour, bond index)]"""
        out: list[list[tuple[int, int]]] = [[] for _ in self.atoms]
        for k, b in enumerate(self.bonds):
            out[b.a].append((b.b, k))
            out[b.b].append((b.a, k))
        return out

    @cached_property
    def bond_index(self) -> dict[tuple[int, int], int]:
        out = {}
        for k, b in enumerate(self.bonds):
            out[(b.a, b.b)] = k
            out[(b.b, b.a)] = k
        return out

    @cached_property
    def explicit_h(self) -> list[int]:
        """Explicit H neighbours per atom."""
        return [sum(1 for n, _ in self.adj[i] if self.atoms[n].symbol == "H") for i in range(len(self.atoms))]

    @cached_property
    def ring_count(self) -> list[int]:
        out = [0] * len(self.atoms)
        for r in self.rings:
            for i in r:
                out[i] += 1
        return out

    @cached_property
    def ring_sizes(self) -> list[frozenset[int]]:
        out: list[set[int]] = [set() for _ in self.atoms]
        for r in self.rings:
            for i in r:
                out[i].add(len(r))
        return [frozenset(s) for s in out]

    @cached_property
    def ring_bond_count(self) -> list[int]:
        out = [0] * len(self.atoms)
        for b in self.bonds:
            if b.ring:
                out[b.a] += 1
                out[b.b] += 1
        return out

    @cached_property
    def element_counts(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for a in self.atoms:
            out[a.z] = out.get(a.z, 0) + 1
        return out

    def degree(self, i: int) -> int:
        return len(self.adj[i])

    def total_h(self, i: int) -> int:
        return self.atoms[i].hcount + self.explicit_h[i]

    def valence(self, i: int) -> int:
        return sum(self.bonds[k].order for _, k in self.adj[i]) + self.atoms[i].hcount

    def heavy_degree(self, i: int) -> int:
        return len(self.adj[i]) - self.explicit_h[i]

    def group(self, i: int) -> int | None:
        return _GROUP.get(self.atoms[i].z)

    def bond_between(self, i: int, j: int) -> Bond | None:
        k = self.bond_index.get((i, j))
        return None if k is None else self.bonds[k]
