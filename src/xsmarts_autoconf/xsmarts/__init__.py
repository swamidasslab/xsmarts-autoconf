"""XSMARTS: vendored LALR(1) SMARTS grammars, typed QueryMol, and the pure-Python
reference matcher + Ambit-style SMIRKS processor (the ``pyref`` adapter).

``xsmarts`` is the superset dialect of every family (formerly "UniSMARTS").
"""

from .build import build_atom_expr, build_querymol, parse_bond_expr, querymol_from_tree
from .canonical import canonicalize_atom_expr, canonicalize_querymol
from .parse import FAMILIES, ParseError, get_parser, parse, parse_tree
from .types import AtomExpr, BondExpr, QueryAtom, QueryBond, QueryMol, Recursive

__all__ = [
    "FAMILIES", "AtomExpr", "BondExpr", "ParseError", "QueryAtom", "QueryBond", "QueryMol",
    "Recursive", "build_atom_expr", "build_querymol", "canonicalize_atom_expr",
    "canonicalize_querymol", "get_parser", "parse", "parse_bond_expr", "parse_tree",
    "querymol_from_tree",
]
