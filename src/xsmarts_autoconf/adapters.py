"""Library adapters. Each is a handful of native calls; no branching logic.

``ADAPTERS`` maps a name to a factory taking ``**options``. Every library is an
optional import: an adapter whose library is missing reports itself
unavailable (``Adapter.available()``) and is skipped by the CLI and tests.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from .adapter import Adapter, Unsupported

# ------------------------------------------------------------------ RDKit


@dataclass
class RDKit(Adapter):
    """Options: ``use_chirality`` (SubstructMatch), ``uniquify``."""

    name: str = "rdkit"

    def version(self) -> str:
        import rdkit

        return rdkit.__version__

    def _query(self, smarts):
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        q = Chem.MolFromSmarts(smarts)
        if q is None:
            raise ValueError("MolFromSmarts returned None")
        return q

    def _mol(self, smiles, explicit_h):
        from rdkit import Chem

        m = Chem.MolFromSmiles(smiles)
        if m is None:
            raise ValueError("reactant parse failed")
        return Chem.AddHs(m) if explicit_h else m

    def parse(self, smarts):
        self._query(smarts)

    def match(self, smarts, smiles, explicit_h):
        q, m = self._query(smarts), self._mol(smiles, explicit_h)
        return len(m.GetSubstructMatches(
            q, uniquify=self.options.get("uniquify", True),
            useChirality=self.options.get("use_chirality", False), maxMatches=100000))

    def apply(self, smirks, smiles, explicit_h):
        from rdkit import Chem
        from rdkit.Chem import AllChem

        rxn = AllChem.ReactionFromSmarts(smirks)
        m = self._mol(smiles, explicit_h)
        out = []
        for outcome in rxn.RunReactants((m,) * rxn.GetNumReactantTemplates()):
            parts = []
            for p in outcome:
                try:
                    p = Chem.RemoveHs(p, sanitize=False)
                except Exception:  # noqa: BLE001
                    pass
                parts.append(Chem.MolToSmiles(p))
            out.append(parts)
        return out

    def sanitize(self, smiles):
        """SanitizeMol must succeed; strip Hs; canonical SMILES."""
        from rdkit import Chem

        m = Chem.MolFromSmiles(smiles, sanitize=False)
        if m is None:
            return None
        try:
            Chem.SanitizeMol(m)
            return Chem.MolToSmiles(Chem.RemoveHs(m))
        except Exception:  # noqa: BLE001
            return None


# ------------------------------------------------------------------ Chematic


@dataclass
class Chematic(Adapter):
    name: str = "chematic"

    def version(self) -> str:
        import chematic

        return chematic.__version__

    def _mol(self, smiles, explicit_h):
        import chematic

        m = chematic.from_smiles(smiles)
        return m.add_hydrogens() if explicit_h else m

    def parse(self, smarts):
        import chematic

        if not chematic.is_valid_smarts(smarts):
            raise ValueError("is_valid_smarts False")

    def match(self, smarts, smiles, explicit_h):
        import chematic

        found = chematic.smarts_find(smarts, self._mol(smiles, explicit_h))
        return len({frozenset(m) for m in found})

    def apply(self, smirks, smiles, explicit_h):
        import chematic

        out = []
        for ps in chematic.run_smirks(smirks, [self._mol(smiles, explicit_h)]):
            parts = []
            for p in ps:
                try:
                    p = p.remove_hydrogens()
                except Exception:  # noqa: BLE001
                    pass
                parts.append(str(p.smiles))
            out.append(parts)
        return out

    def sanitize(self, smiles):
        """Reparse + remove_hydrogens; None if chematic rejects."""
        import chematic

        try:
            m = chematic.from_smiles(smiles)
            try:
                m = m.remove_hydrogens()
            except Exception:  # noqa: BLE001
                pass
            return str(m.smiles) or None
        except Exception:  # noqa: BLE001
            return None


# ------------------------------------------------------------------ Open Babel


@dataclass
class OpenBabel(Adapter):
    name: str = "openbabel"

    def __post_init__(self):
        try:
            from openbabel import openbabel as ob
        except ImportError:
            return
        ob.obErrorLog.SetOutputLevel(-1)  # its C++ log writes to stdout
        ob.obErrorLog.StopLogging()

    def version(self) -> str:
        from openbabel import openbabel as ob

        return ob.OBReleaseVersion()

    def _mol(self, smiles, explicit_h):
        from openbabel import openbabel as ob

        conv = ob.OBConversion()
        conv.SetInFormat("smi")
        m = ob.OBMol()
        if not conv.ReadString(m, smiles):
            raise ValueError("reactant parse failed")
        if explicit_h:
            m.AddHydrogens()
        return m

    def _pattern(self, smarts):
        from openbabel import openbabel as ob

        ob.obErrorLog.SetOutputLevel(0)
        p = ob.OBSmartsPattern()
        if not p.Init(smarts):
            raise ValueError("OBSmartsPattern.Init False")
        return p

    def parse(self, smarts):
        self._pattern(smarts)

    def match(self, smarts, smiles, explicit_h):
        p, m = self._pattern(smarts), self._mol(smiles, explicit_h)
        p.Match(m)
        return len(p.GetUMapList())

    def apply(self, smirks, smiles, explicit_h):
        from openbabel import openbabel as ob

        left, _, right = smirks.partition(">>")
        ts = ob.OBChemTsfm()
        if not ts.Init(left, right):
            raise ValueError("OBChemTsfm.Init failed")
        m = self._mol(smiles, explicit_h)
        if not ts.Apply(m):
            return []
        m.DeleteHydrogens()
        conv = ob.OBConversion()
        conv.SetOutFormat("can")
        return [conv.WriteString(m).strip().split()[0]]

    def sanitize(self, smiles):
        """Reparse, delete Hs, canonical SMILES."""
        from openbabel import openbabel as ob

        conv = ob.OBConversion()
        conv.SetInFormat("smi")
        conv.SetOutFormat("can")
        m = ob.OBMol()
        if not conv.ReadString(m, smiles):
            return None
        m.DeleteHydrogens()
        return conv.WriteString(m).strip().split()[0] or None


# ------------------------------------------------------------------ CDK


@dataclass
class CDK(Adapter):
    """CDK from the BioTransformer jar: ``SmartsPattern`` for parse/match
    (the BioTransformer *gate* path), Ambit ``SMIRKSManager`` for apply."""

    name: str = "cdk"

    def version(self) -> str:
        from . import java

        return str(java.jclass("org.openscience.cdk.CDK").getVersion()) + "+ambit(bt-jar)"

    def _mol(self, smiles, explicit_h):
        from . import java

        m = java.parse_smiles(smiles)
        if explicit_h:
            java.jclass("org.openscience.cdk.tools.manipulator.AtomContainerManipulator"
                        ).convertImplicitToExplicitHydrogens(m)
        return m

    def _pattern(self, smarts):
        from . import java

        return java.jclass("org.openscience.cdk.smarts.SmartsPattern").create(smarts, java.start())

    def parse(self, smarts):
        self._pattern(smarts)

    def match(self, smarts, smiles, explicit_h):
        return int(self._pattern(smarts).matchAll(self._mol(smiles, explicit_h)).uniqueAtoms().count())

    def apply(self, smirks, smiles, explicit_h):
        """Raw Ambit SMIRKSManager (result processing on, BioTransformer's
        other flags at Ambit defaults)."""
        from . import java

        mgr = java.jclass("ambit2.smarts.SMIRKSManager")(java.start())
        mgr.setFlagProcessResultStructures(True)
        rxn = mgr.parse(smirks)
        if mgr.hasErrors():
            raise ValueError(str(mgr.getErrors()))
        res = mgr.applyTransformationWithSingleCopyForEachPos(self._mol(smiles, explicit_h), None, rxn)
        if res is None:
            return []
        acm = java.jclass("org.openscience.cdk.tools.manipulator.AtomContainerManipulator")
        out = []
        for i in range(int(res.getAtomContainerCount())):
            ac = res.getAtomContainer(i)
            acm.suppressHydrogens(ac)
            out.append(java.unique_smiles(ac))
        return out

    def sanitize(self, smiles):
        from . import java

        return java.cdk_sanitize(smiles)


@dataclass
class BioTransformer(CDK):
    """BioTransformer's own Java pipeline for one SMIRKS:
    ``generateAllMetabolitesFromAtomContainer(mol, SMIRKSReaction, false)`` on a
    BioTransformer-prepared substrate (atom typing, Daylight aromaticity,
    explicit H; AMBIT.md B0-B5). Products are post-split fragments with
    cofactors / small byproducts dropped (B1, B2) and validity-filtered (B5a).
    All outcomes come back as one flat fragment list, so the whole result is a
    single outcome whose objects are the fragments. Matching (the rule *gate*)
    is CDK SmartsPattern, inherited. ``explicit_h`` is ignored: BioTransformer
    always prepares explicit H."""

    name: str = "biotransformer"

    def version(self) -> str:
        return super().version().replace("+ambit(bt-jar)", "+biotransformer(fat-jar)")

    def apply(self, smirks, smiles, explicit_h):
        from . import java

        mgr = java.bt_smirks_manager()
        rxn = mgr.parse(smirks)
        if str(mgr.getErrors()).strip():
            raise ValueError(str(mgr.getErrors()))
        mets = java.bt_helper().generateAllMetabolitesFromAtomContainer(java.bt_prepare(smiles), rxn, False)
        if mets is None or mets.getAtomContainerCount() == 0:
            return []
        return [[java.unique_smiles(mets.getAtomContainer(i)) for i in range(mets.getAtomContainerCount())]]


# ------------------------------------------------------------------ Python reference


# Flags the reference engine implements, as {flag: (Profile field, {value: setting})}.
# This table is the whole autoconf -> engine wiring: a config file selects a value
# per flag and :meth:`PyRef.from_config` turns it into a Profile.
PYREF_FLAGS: dict[str, tuple[str, dict[str, bool]]] = {
    "match.ring_size_semantics": ("ring_size_any", {"any_ring": True, "smallest_ring": False}),
    "match.single_bond_vs_aromatic": ("single_excludes_aromatic",
                                      {"excludes_aromatic": True, "includes_aromatic": False}),
    # pyref's False setting only reaches Kekule-written input (round trip finding)
    "match.double_bond_vs_aromatic": ("double_excludes_aromatic",
                                      {"excludes_aromatic": True, "kekule_input_only": False}),
    "match.or_with_any_atom": ("or_drops_any", {"correct": False, "drops_any": True}),
    "match.nested_recursive": ("nested_recursive_true", {"evaluated": False, "always_true": True}),
}


@dataclass
class PyRef(Adapter):
    """Vendored ``xsmarts`` reference matcher + Ambit-style processor (pure
    Python; aromaticity perception uses chematic).

    ``options`` are Profile fields (see ``PYREF_FLAGS``); this is the
    configurable engine used for autoconf round-trip tests."""

    name: str = "pyref"
    options: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, flags: dict[str, str]) -> PyRef:
        opts = {}
        for flag, value in flags.items():
            if flag in PYREF_FLAGS and value in PYREF_FLAGS[flag][1]:
                fld, table = PYREF_FLAGS[flag]
                opts[fld] = table[value]
        return cls(options=opts)

    def version(self) -> str:
        from . import __version__

        import chematic  # noqa: F401  (perception backend)

        return f"xsmarts-{__version__}"

    def _profile(self):
        from .xsmarts.match import Profile

        return Profile("autoconf", **self.options)

    def _mol(self, smiles, explicit_h):
        from .xsmarts.perceive import mol_from_smiles

        return mol_from_smiles(smiles, explicit_h=explicit_h)

    def parse(self, smarts):
        from .xsmarts import build_querymol

        build_querymol(smarts, "xsmarts")

    def match(self, smarts, smiles, explicit_h):
        from .xsmarts import build_querymol
        from .xsmarts.match import Matcher

        q = build_querymol(smarts, "xsmarts")
        if q.atom_role and any(r != "reactant" for r in q.atom_role if r):
            raise Unsupported("reaction query")
        mt = Matcher(q, self._profile())
        return len({frozenset(m.values()) for m in mt.matches(self._mol(smiles, explicit_h))})

    def apply(self, smirks, smiles, explicit_h):
        from .xsmarts.ambit import AmbitReaction

        rx = AmbitReaction.compile(smirks, self._profile())
        return [_mol_smiles(p) for p in rx.apply(self._mol(smiles, explicit_h))]


def _mol_smiles(mol) -> str:
    from rdkit import Chem

    rw = Chem.RWMol()
    for i, a in enumerate(mol.atoms):
        at = Chem.Atom(0 if i in mol.dummies else Chem.GetPeriodicTable().GetAtomicNumber(a.symbol))
        at.SetFormalCharge(a.charge)
        at.SetNoImplicit(True)
        at.SetNumExplicitHs(a.hcount)
        rw.AddAtom(at)
    bt = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}
    for b in mol.bonds:
        rw.AddBond(b.a, b.b, bt.get(b.order, Chem.BondType.AROMATIC))
    m = rw.GetMol()
    m.UpdatePropertyCache(strict=False)
    try:
        m = Chem.RemoveHs(m, sanitize=False)
    except Exception:  # noqa: BLE001
        pass
    return Chem.MolToSmiles(m)


# ------------------------------------------------------------------ xenosmarts (Rust engine)

# autoconf flag -> (xenosmarts profile flag, {value: setting}). Like PYREF_FLAGS,
# this table is the whole config -> engine wiring for round-trip tests.
XENOSMARTS_FLAGS: dict[str, tuple[str, dict[str, bool]]] = {
    "match.ring_size_semantics": ("ring_size_any", {"any_ring": True, "smallest_ring": False}),
    "match.or_with_any_atom": ("or_drops_any", {"correct": False, "drops_any": True}),
    "match.nested_recursive": ("nested_recursive_true", {"evaluated": False, "always_true": True}),
    "match.single_bond_vs_aromatic": ("kekule_match", {"excludes_aromatic": False, "includes_aromatic": True}),
    "match.double_bond_vs_aromatic": ("kekule_match", {"excludes_aromatic": False, "includes_aromatic": True}),
    "match.compound_bond_kekule": ("compound_bond_kekule", {"aromatic_aware": False, "kekule_order": True}),
}


@dataclass
class Xenosmarts(Adapter):
    """``xenosmarts`` Rust engine via its Python module (installed separately;
    no wheels are shipped here). If it is not importable, set
    ``XSMARTS_XENOSMARTS_PATH`` to the directory containing the module.

    Options: ``profile`` (cdk | cdk-gate | ambit | native, default cdk),
    ``dialect`` (default xsmarts), any profile flag name -> bool, and
    ``pipeline`` = ambit (raw ``apply``) | bt (``bt_metabolites``)."""

    name: str = "xenosmarts"

    @classmethod
    def from_config(cls, flags: dict[str, str], **base) -> Xenosmarts:
        opts = dict(base)
        for flag, value in flags.items():
            if flag in XENOSMARTS_FLAGS and value in XENOSMARTS_FLAGS[flag][1]:
                fld, table = XENOSMARTS_FLAGS[flag]
                opts[fld] = table[value]
        return cls(options=opts)

    def _x(self):
        p = os.environ.get("XSMARTS_XENOSMARTS_PATH")
        if p and p not in sys.path:
            sys.path.insert(0, p)
        import xenosmarts

        return xenosmarts

    def version(self) -> str:
        x = self._x()
        return str(getattr(x, "__version__", "local-build"))

    def _flags(self):
        names = {f for _, fl in self._x().profile_flags() for f, _ in fl}
        return {k: bool(v) for k, v in self.options.items() if k in names}

    def _mol(self, smiles, explicit_h):
        m = self._x().Mol.from_smiles(smiles)
        return m.with_virtual_h() if explicit_h else m

    def _matcher(self, smarts):
        o = self.options
        # The external engine's name for the XSMARTS superset dialect.
        dialect = {"xsmarts": "unismarts"}.get(o.get("dialect", "xsmarts"), o.get("dialect"))
        return self._x().Matcher(smarts, dialect, o.get("profile", "cdk"), self._flags())

    def parse(self, smarts):
        self._matcher(smarts)

    def match(self, smarts, smiles, explicit_h):
        return int(self._matcher(smarts).count(self._mol(smiles, explicit_h)))

    def apply(self, smirks, smiles, explicit_h):
        rx = self._x().AmbitReaction(smirks)
        m = self._mol(smiles, explicit_h)
        if self.options.get("pipeline") == "bt":
            frags = rx.bt_metabolites(m)
            return [[_xmol_smiles(f) for f in frags]] if frags else []
        return [_xmol_smiles(p) for p in rx.apply(m)]


def _xmol_smiles(xm) -> str:
    from rdkit import Chem

    rw = Chem.RWMol()
    pt = Chem.GetPeriodicTable()
    for sym, charge, h, arom, iso, dummy in xm.atoms():
        at = Chem.Atom(0 if dummy else pt.GetAtomicNumber(sym))
        at.SetFormalCharge(charge)
        at.SetNoImplicit(True)
        at.SetNumExplicitHs(h)
        if iso:
            at.SetIsotope(iso)
        rw.AddAtom(at)
    bt = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}
    for a, b, order, arom, ring in xm.bonds():
        rw.AddBond(a, b, bt.get(order, Chem.BondType.SINGLE))
    m = rw.GetMol()
    m.UpdatePropertyCache(strict=False)
    try:
        m = Chem.RemoveHs(m, sanitize=False)
    except Exception:  # noqa: BLE001
        pass
    return Chem.MolToSmiles(m)


ADAPTERS = {
    "rdkit": RDKit,
    "chematic": Chematic,
    "openbabel": OpenBabel,
    "cdk": CDK,
    "biotransformer": BioTransformer,
    "pyref": PyRef,
    "xenosmarts": Xenosmarts,
}


def make(name: str, **options) -> Adapter:
    return ADAPTERS[name](options=options)
