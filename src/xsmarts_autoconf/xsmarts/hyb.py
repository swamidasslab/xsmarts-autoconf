"""Canonical hybridization kinds and per-dialect ``^n`` digit maps.

QueryMol stores *kinds* (shared meaning). Parse maps dialect digits → kind;
write maps kind → dialect digit or raises if the target has no slot.
"""

from __future__ import annotations

from typing import Literal

from .parse import Family

HybKind = Literal[
    "S",
    "SP",
    "SP2",
    "SP3",
    "SP3D",
    "SP3D2",
    "SP3D3",
    "SP3D4",
    "SP3D5",
    "SQ_PLANAR",
    "TRIG_BIPY",
    "OCTAHEDRAL",
]

# RDKit / chematic: ^0=S … ^5=SP3D2
_RDKIT_CHEMATIC: dict[int, HybKind] = {
    0: "S",
    1: "SP",
    2: "SP2",
    3: "SP3",
    4: "SP3D",
    5: "SP3D2",
}

# CDK / OpenEye-style: ^1=SP1 … ^8=SP3D5 (no S)
_CDK: dict[int, HybKind] = {
    1: "SP",
    2: "SP2",
    3: "SP3",
    4: "SP3D",  # SP3D1
    5: "SP3D2",
    6: "SP3D3",
    7: "SP3D4",
    8: "SP3D5",
}

# Open Babel GetHyb: ^1=sp … ^6=octahedral (^4/^5 are NOT RDKit SP3D/SP3D2)
_OPENBABEL: dict[int, HybKind] = {
    1: "SP",
    2: "SP2",
    3: "SP3",
    4: "SQ_PLANAR",
    5: "TRIG_BIPY",
    6: "OCTAHEDRAL",
}

DIGIT_TO_KIND: dict[str, dict[int, HybKind]] = {
    "rdkit": _RDKIT_CHEMATIC,
    "chematic": _RDKIT_CHEMATIC,
    "cdk": _CDK,
    "openbabel": _OPENBABEL,
}

KIND_TO_DIGIT: dict[str, dict[HybKind, int]] = {
    fam: {kind: digit for digit, kind in table.items()}
    for fam, table in DIGIT_TO_KIND.items()
}


def digit_to_kind(family: Family | str, digit: int) -> HybKind:
    """Map a dialect ``^n`` digit to a canonical kind."""
    table = DIGIT_TO_KIND.get(family)
    if table is None:
        raise ValueError(f"family {family!r} has no hybridization extension")
    try:
        return table[digit]
    except KeyError as e:
        slots = ",".join(f"^{d}" for d in sorted(table))
        raise ValueError(
            f"{family} hybridization has no kind for ^{digit} (slots: {slots})"
        ) from e


def kind_to_digit(family: Family | str, kind: HybKind | str) -> int:
    """Map a canonical kind to a dialect ``^n`` digit."""
    table = KIND_TO_DIGIT.get(family)
    if table is None:
        raise ValueError(f"family {family!r} has no hybridization extension")
    try:
        return table[kind]  # type: ignore[index]
    except KeyError as e:
        slots = ", ".join(sorted(table))
        raise ValueError(
            f"{family} has no ^{{n}} slot for hybridization {kind!r} "
            f"(available: {slots})"
        ) from e
