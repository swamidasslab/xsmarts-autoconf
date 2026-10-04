"""Parse SMARTS with family-specific LALR(1) Lark grammars."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from lark import Lark, Tree
from lark.exceptions import LarkError, UnexpectedInput, VisitError

Family = Literal["opensmarts", "rdkit", "cdk", "chematic", "openbabel", "xsmarts"]

FAMILIES: tuple[Family, ...] = (
    "opensmarts",
    "rdkit",
    "cdk",
    "chematic",
    "openbabel",
    "xsmarts",  # superset of all of the above; see dialect.py
)

_GRAMMAR_DIR = Path(__file__).resolve().parent / "grammars"


class ParseError(ValueError):
    """SMARTS string is not valid for the requested family grammar."""

    def __init__(self, smarts: str, family: Family, cause: Exception):
        self.smarts = smarts
        self.family = family
        self.cause = cause
        super().__init__(f"{family} SMARTS parse failed: {cause}")


# ``start`` = full reaction/mol; fragment starts used by writer round-trips.
_START_SYMBOLS = ("start", "bracket_atom", "atom_expression")


@lru_cache(maxsize=None)
def get_parser(family: Family = "opensmarts") -> Lark:
    """Return a cached LALR(1) parser for ``family``."""
    if family not in FAMILIES:
        raise ValueError(f"unknown SMARTS family {family!r}; choose from {FAMILIES}")
    path = _GRAMMAR_DIR / f"{family}.lark"
    return Lark.open(
        str(path),
        parser="lalr",
        start=list(_START_SYMBOLS),
        maybe_placeholders=False,
        import_paths=[str(_GRAMMAR_DIR)],
    )


def parse_tree(
    smarts: str,
    family: Family = "opensmarts",
    *,
    start: str = "start",
) -> Tree:
    """Parse ``smarts`` and return the Lark parse tree.

    Parameters
    ----------
    start:
        Grammar start symbol. Default ``start`` (reaction/mol). Use
        ``bracket_atom`` / ``atom_expression`` for atom-fragment checks.
    """
    if start not in _START_SYMBOLS:
        raise ValueError(f"unknown start symbol {start!r}; choose from {_START_SYMBOLS}")
    try:
        return get_parser(family).parse(smarts, start=start)
    except (UnexpectedInput, LarkError, VisitError) as exc:
        raise ParseError(smarts, family, exc) from exc


def parse(smarts: str, family: Family = "opensmarts") -> Tree:
    """Alias for :func:`parse_tree`."""
    return parse_tree(smarts, family)
