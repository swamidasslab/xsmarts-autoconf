"""Adapter base: the thin per-library surface autoconf and the fuzzer drive.

A library adapter overrides a handful of methods that return *native* results:

- ``parse(smarts)``                      -> None, raise on rejection
- ``match(smarts, smiles, explicit_h)``  -> number of unique (atom-set) matches
- ``apply(smirks, smiles, explicit_h)``  -> one entry per outcome: a list of
  product-object SMILES (or a single SMILES string for one object)
- ``sanitize(smiles)``                   -> lib-native sanitized SMILES or None (reject)

Everything else (error capture, unsupported ops, SMILES normalization, the
observation string) is centralized in :meth:`Adapter.observe`, so adapters stay
a few lines each. Raise :class:`Unsupported` for an op the library lacks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

PARENT = Path(__file__).resolve().parents[2]
if str(PARENT / "scripts") not in sys.path:
    sys.path.insert(0, str(PARENT / "scripts"))


class Unsupported(Exception):
    """The adapter has no way to run this op."""


@dataclass(frozen=True)
class Case:
    """One executable example. ``op`` is parse | match | apply."""

    id: str
    op: str
    query: str
    mol: str | None = None
    explicit_h: bool = False
    view: str = "products"
    """apply only: ``products`` (raw edit set, all objects joined), ``sanitized``
    (lib-native sanitize, rejects dropped), ``count`` (number of outcomes, with
    dups) or ``objects`` (product objects per outcome, ``A + B``)."""
    note: str = ""
    orderings: int = 0
    """Also observe on this many deterministic re-orderings of ``mol`` and
    report the set of outcomes (``a / b``). Use for perception with several
    valid answers (non-unique SSSR, enumeration order): the observation stays
    deterministic without introspecting the library's molecule object."""
    spellings: tuple[str, ...] = ()
    """Explicit alternative spellings of ``mol`` to observe as well (result is
    the outcome set, like ``orderings``). Name the spellings that surface a
    known order dependence so it is checked every run, not by chance."""
    fixed_spelling: bool = False
    """The SMILES spelling is the point of the case; stability checks must
    not reorder it."""


def reorderings(smiles: str, n: int) -> list[str]:
    """Up to ``n`` systematic equivalent spellings of ``smiles`` (stereo kept):
    the SMILES rooted at each atom in turn (atom 0 first, then 1, ...), then
    the reversed atom numbering. Deterministic and order-targeted, so
    start-atom / traversal-order dependence surfaces reproducibly."""
    from rdkit import Chem

    m = Chem.MolFromSmiles(smiles)
    if m is None or n <= 0:
        return []
    cands = [Chem.MolToSmiles(m, rootedAtAtom=i, canonical=False) for i in range(m.GetNumAtoms())]
    rev = Chem.RenumberAtoms(m, list(reversed(range(m.GetNumAtoms()))))
    cands.append(Chem.MolToSmiles(rev, canonical=False))
    out = []
    for c in cands:
        if c != smiles and c not in out:
            out.append(c)
    return out[:n]


@dataclass
class Observation:
    case: Case
    text: str
    """Normalized, comparable outcome: ``ok`` | ``error`` | ``unsupported`` |
    ``match:N`` | ``products:A|B`` | ``outcomes:N``."""
    detail: str = ""
    """Native output or error message (evidence only, never compared)."""


def canon(smiles: str) -> str:
    """Strip SMILES-dialect noise (atom order, ``C(C)O`` vs ``CCO``) without
    changing chemistry: RDKit parse with sanitize off, then canonical write.
    Bracket labels such as CDK's ``[C]`` (zero H) are kept: they are chemistry."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    m = Chem.MolFromSmiles(smiles, sanitize=False)
    if m is None:
        return f"?{smiles}"
    try:
        m.UpdatePropertyCache(strict=False)
        out = Chem.MolToSmiles(m)
        # The unsanitized writer can drop brackets that pin H counts ([C] -> C);
        # spell every H explicitly when the short form would change chemistry.
        if _h_signature(out) != _h_signature_mol(m):
            out = Chem.MolToSmiles(m, allHsExplicit=True)
        return out
    except Exception:  # noqa: BLE001
        return f"?{smiles}"


def _h_signature_mol(m) -> list:
    return sorted((a.GetAtomicNum(), a.GetFormalCharge(), a.GetTotalNumHs()) for a in m.GetAtoms())


def _h_signature(smiles: str) -> list | None:
    from rdkit import Chem

    m = Chem.MolFromSmiles(smiles, sanitize=False)
    if m is None:
        return None
    m.UpdatePropertyCache(strict=False)
    return _h_signature_mol(m)


def canon_set(smiles: str) -> str:
    """Canonicalize a ``.``-joined product set, component order independent."""
    return ".".join(sorted(canon(p) for p in smiles.split(".") if p))


@dataclass
class Adapter:
    """Base adapter. Subclasses set ``name`` and override the native methods."""

    name: str = "base"
    options: dict = field(default_factory=dict)

    # ----- override these -----

    def version(self) -> str:
        return "unknown"

    def parse(self, smarts: str) -> None:
        raise Unsupported

    def match(self, smarts: str, smiles: str, explicit_h: bool) -> int:
        raise Unsupported

    def apply(self, smirks: str, smiles: str, explicit_h: bool) -> list[list[str] | str]:
        raise Unsupported

    def sanitize(self, smiles: str) -> str | None:
        raise Unsupported

    # ----- centralized logic -----

    def label(self) -> str:
        if not self.options:
            return self.name
        opts = ",".join(f"{k}={v}" for k, v in sorted(self.options.items()))
        return f"{self.name}[{opts}]"

    def observe(self, case: Case) -> Observation:
        if (case.orderings or case.spellings) and case.mol:
            from dataclasses import replace

            mols = [case.mol, *case.spellings, *reorderings(case.mol, case.orderings)]
            obs = [self._observe1(replace(case, mol=m, orderings=0, spellings=()))
                   for m in dict.fromkeys(mols)]
            texts = sorted({o.text for o in obs})
            return Observation(case, " / ".join(texts), " | ".join(o.detail for o in obs if o.detail))
        return self._observe1(case)

    def _observe1(self, case: Case) -> Observation:
        try:
            text, detail = self._run(case)
        except Unsupported as e:
            return Observation(case, "unsupported", str(e))
        except Exception as e:  # noqa: BLE001
            return Observation(case, "error", f"{type(e).__name__}: {e}"[:300])
        return Observation(case, text, detail)

    def _run(self, case: Case) -> tuple[str, str]:
        if case.op == "parse":
            self.parse(case.query)
            return "ok", ""
        if case.op == "match":
            n = self.match(case.query, case.mol, case.explicit_h)
            return f"match:{n}", ""
        if case.op == "apply":
            outs = [[o] if isinstance(o, str) else list(o)
                    for o in self.apply(case.query, case.mol, case.explicit_h)]
            detail = " | ".join(" + ".join(o) for o in outs)
            if case.view == "count":
                return f"outcomes:{len(outs)}", detail
            if case.view == "objects":
                # Product objects per outcome: one disconnected object ("C.O")
                # vs separate objects ("C + O"); dropped fragments show here too.
                per = {" + ".join(sorted(canon_set(x) for x in o)) for o in outs}
                return "objects:" + "|".join(sorted(per)), detail
            flat = [".".join(o) for o in outs]
            if case.view == "sanitized":
                flat = [s for s in (self._sanitize_set(o) for o in flat) if s is not None]
            return "products:" + "|".join(sorted({canon_set(o) for o in flat})), detail
        raise ValueError(f"unknown op {case.op!r}")

    def _sanitize_set(self, smiles: str) -> str | None:
        parts = [self.sanitize(p) for p in smiles.split(".") if p]
        return None if any(p is None for p in parts) else ".".join(parts)
