"""BioTransformer post-steps after Ambit (docs/xenosmarts/AMBIT.md B1–B4).

``postprocess(products)`` reproduces ``Biotransformer.generateAllMetabolites
FromAtomContainer`` after ``applyTransformationWithSingleCopyForEachPos``:
split each product into connected fragments (B1), drop fragments that fail
``isValidMetabolte`` (B5a) or are on the ``isUnneccessaryMetabolite``
blocklist (B2). The final ``preprocessContainer`` (re-typing, aromaticity)
does not change the molecule's identity and is not reproduced.
"""

from __future__ import annotations

from functools import lru_cache

from .build import build_querymol
from .match import CDK, Matcher
from .mol import Bond, Mol

# biotransformer.validateModels.InValidSMARTS (from the jar's constants)
INVALID_SMARTS = (
    "[#8]-[#6](-[#8])-[#8]-*",      # COOO
    "[#8]-[#6](=O)-[#8]-*",         # C=OOO
    "[#8]C([#8])([#8])[#8]-*",      # COOOO
    "[#8]-[#6]-1-[#6]-[#8]-1",      # HydroxylEpOxide
    "[H][#8]-[#6]-[#8][H]",         # DihydroxylOnOnecarbon
    "[#6]=C=O",                     # C=C=O
    "O=[#6]-1-[#6]-[#8]-1",         # O=C1CO1
    "[#8]-[#8]",                    # O-O
    "O=O",                          # O=O
)

# ChemStructureExplorer.isUnneccessaryMetabolite, probed (AMBIT.md B2): as
# (heavy-atom formula, charge-free) keys; H2 handled separately.
UNNECESSARY = {"F": 1, "Cl": 1, "Br": 1, "I": 1}


@lru_cache(maxsize=None)
def _invalid_matchers() -> tuple[Matcher, ...]:
    return tuple(Matcher(build_querymol(s, "cdk"), CDK) for s in INVALID_SMARTS)


def fragments(m: Mol) -> list[Mol]:
    """B1: connected components (``ChemStructureExplorer.checkConnectivity``)."""
    parent = list(range(len(m.atoms)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for b in m.bonds:
        parent[find(b.a)] = find(b.b)
    groups: dict[int, list[int]] = {}
    for i in range(len(m.atoms)):
        groups.setdefault(find(i), []).append(i)
    out = []
    for idx in groups.values():
        ren = {o: n for n, o in enumerate(idx)}
        frag = Mol([m.atoms[i] for i in idx],
                   [Bond(ren[b.a], ren[b.b], b.order) for b in m.bonds if b.a in ren])
        frag.dummies = frozenset(ren[i] for i in m.dummies if i in ren)
        out.append(frag)
    return out


def is_valid_metabolite(m: Mol) -> bool:
    """``Biotransformer.isValidMetabolte`` (bytecode): no InValidSMARTS match,
    at least one non-H atom and at least one atom whose symbol is ``C``
    (an Ambit dummy reads as ``R``, not ``C``)."""
    if m.dummies:  # dummies are R (atomic number 0) when BT checks validity
        from .mol import Atom

        m = Mol([Atom("R", a.charge, a.hcount) if i in m.dummies else a for i, a in enumerate(m.atoms)],
                m.bonds)
    if any(mt.exists(m) for mt in _invalid_matchers()):
        return False
    heavy = sum(1 for a in m.atoms if a.symbol != "H")
    carbon = sum(1 for a in m.atoms if a.symbol == "C")
    return heavy >= 1 and carbon >= 1


def _formula(m: Mol) -> tuple:
    counts: dict[str, int] = {}
    for a in m.atoms:
        counts[a.symbol] = counts.get(a.symbol, 0) + 1 + (a.hcount if a.symbol != "H" else 0)
        if a.hcount and a.symbol != "H":
            counts["H"] = counts.get("H", 0) + a.hcount
            counts[a.symbol] -= a.hcount
    return tuple(sorted(counts.items())), sum(a.charge for a in m.atoms)


# Neutral molecules isUnneccessaryMetabolite rejects (probed): HF, HCl, HBr,
# HI, H2O, NH3, H2SO4, H3PO4, CH2O, CO2, H2.
_UNNECESSARY_FORMULAS = {
    (tuple(sorted({"H": 1, "F": 1}.items())), 0), (tuple(sorted({"H": 1, "Cl": 1}.items())), 0),
    (tuple(sorted({"H": 1, "Br": 1}.items())), 0), (tuple(sorted({"H": 1, "I": 1}.items())), 0),
    (tuple(sorted({"H": 2, "O": 1}.items())), 0), (tuple(sorted({"H": 3, "N": 1}.items())), 0),
    (tuple(sorted({"H": 2, "S": 1, "O": 4}.items())), 0), (tuple(sorted({"H": 3, "P": 1, "O": 4}.items())), 0),
    (tuple(sorted({"C": 1, "H": 2, "O": 1}.items())), 0), (tuple(sorted({"C": 1, "O": 2}.items())), 0),
    (tuple(sorted({"H": 2}.items())), 0),
}


def is_unnecessary(m: Mol) -> bool:
    """B2 blocklist, by formula + charge (each entry has a single structure).

    Checked before the dummy repair, so a dummy-carbon formaldehyde (``O=[*H2]``)
    is *not* recognised and survives, as in BioTransformer.
    """
    if m.dummies:
        return False
    return _formula(m) in _UNNECESSARY_FORMULAS


def postprocess(products: list[Mol]) -> list[Mol]:
    out = []
    for p in products:
        for f in fragments(p):
            if not is_valid_metabolite(f) or is_unnecessary(f):
                continue
            out.append(f)
    return out
