"""JVM bridge for the Java-side adapters (CDK SmartsPattern, Ambit SMIRKSManager,
BioTransformer's metabolite pipeline). Optional: needs ``jpype1`` and a jar.

Configuration (environment):

- ``XSMARTS_BIOTRANSFORMER_JAR``: path to the BioTransformer 3.0 fat jar
  (bundles CDK and Ambit). Required for ``cdk`` and ``biotransformer``.
- ``XSMARTS_BIOTRANSFORMER_RUN``: BioTransformer working directory (its
  ``config``/``database`` folders); default: the jar's directory.
- ``JAVA_HOME``: JDK to load; default: JPype's default JVM.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_BT_HELPER = None


class JavaUnavailable(RuntimeError):
    pass


def jar_path() -> Path:
    p = os.environ.get("XSMARTS_BIOTRANSFORMER_JAR")
    if not p:
        raise JavaUnavailable("set XSMARTS_BIOTRANSFORMER_JAR to the BioTransformer 3.0 jar")
    path = Path(p).expanduser()
    if not path.is_file():
        raise JavaUnavailable(f"XSMARTS_BIOTRANSFORMER_JAR not found: {path}")
    return path


def run_dir() -> Path:
    return Path(os.environ.get("XSMARTS_BIOTRANSFORMER_RUN") or jar_path().parent).expanduser()


def _jvm_path() -> str:
    import jpype

    home = os.environ.get("JAVA_HOME")
    if home:
        for rel in ("lib/server/libjvm.dylib", "lib/server/libjvm.so", "bin/server/jvm.dll"):
            if (Path(home) / rel).exists():
                return str(Path(home) / rel)
    try:
        return jpype.getDefaultJVMPath()
    except Exception as e:  # noqa: BLE001
        raise JavaUnavailable("no JVM found: set JAVA_HOME to a JDK") from e


@lru_cache(maxsize=1)
def start() -> object:
    """Start the JVM once; return the CDK SilentChemObjectBuilder."""
    try:
        import jpype
        import jpype.imports  # noqa: F401
    except ImportError as e:
        raise JavaUnavailable("jpype1 not installed (pip install xsmarts-autoconf[java])") from e
    jar = jar_path()
    if not jpype.isJVMStarted():
        jpype.startJVM(_jvm_path(), f"-Duser.dir={run_dir().resolve()}", classpath=[str(jar.resolve())])
    return jpype.JClass("org.openscience.cdk.silent.SilentChemObjectBuilder").getInstance()


def jclass(name: str):
    import jpype

    start()
    return jpype.JClass(name)


def parse_smiles(smiles: str):
    return jclass("org.openscience.cdk.smiles.SmilesParser")(start()).parseSmiles(smiles)


def unique_smiles(mol) -> str:
    return str(jclass("org.openscience.cdk.smiles.SmilesGenerator").unique().create(mol))


@lru_cache(maxsize=1)
def bt_smirks_manager():
    """SMIRKSManager configured as BioTransformer configures it."""
    mgr = jclass("ambit2.smarts.SMIRKSManager")(start())
    mgr.setFlagApplyStereoTransformation(False)
    mgr.setFlagCheckResultStereo(True)
    mgr.setFlagFilterEquivalentMappings(True)
    mgr.setFlagProcessResultStructures(True)
    mgr.setFlagAddImplicitHAtomsOnResultProcess(True)
    return mgr


def bt_prepare(smiles: str):
    """BioTransformer substrate preparation: preprocessContainer (atom typing,
    Daylight aromaticity over Cycles.or(all, all(6)), 2D coordinates), then
    explicit H."""
    mol = parse_smiles(smiles)
    acm = jclass("org.openscience.cdk.tools.manipulator.AtomContainerManipulator")
    acm.percieveAtomTypesAndConfigureAtoms(mol)
    Cycles = jclass("org.openscience.cdk.graph.Cycles")
    arom = jclass("org.openscience.cdk.aromaticity.Aromaticity")(
        jclass("org.openscience.cdk.aromaticity.ElectronDonation").daylight(),
        Cycles.or_(Cycles.all(), Cycles.all(6)))
    arom.apply(mol)
    try:
        sdg = jclass("org.openscience.cdk.layout.StructureDiagramGenerator")()
        sdg.setMolecule(mol)
        sdg.generateCoordinates()
        mol = sdg.getMolecule()
    except Exception:  # noqa: BLE001
        pass
    acm.convertImplicitToExplicitHydrogens(mol)
    return mol


def bt_helper():
    """Cached Phase2BTransformer exposing generateAllMetabolitesFromAtomContainer."""
    global _BT_HELPER
    if _BT_HELPER is None:
        prev = os.getcwd()
        try:
            os.chdir(run_dir())
            name = jclass("biotransformer.biosystems.BioSystem$BioSystemName")
            _BT_HELPER = jclass("biotransformer.btransformers.Phase2BTransformer")(name.HUMAN, True, True)
        finally:
            os.chdir(prev)
    return _BT_HELPER


def cdk_sanitize(smiles: str) -> str | None:
    """CDK-only Layer S: atom types + Daylight aromaticity + unique SMILES."""
    try:
        mol = parse_smiles(smiles)
        acm = jclass("org.openscience.cdk.tools.manipulator.AtomContainerManipulator")
        acm.percieveAtomTypesAndConfigureAtoms(mol)
        try:
            jclass("org.openscience.cdk.aromaticity.Aromaticity")(
                jclass("org.openscience.cdk.aromaticity.ElectronDonation").daylight(),
                jclass("org.openscience.cdk.graph.Cycles").all()).apply(mol)
        except Exception:  # noqa: BLE001
            pass
        try:
            acm.suppressHydrogens(mol)
        except Exception:  # noqa: BLE001
            pass
        return unique_smiles(mol)
    except Exception:  # noqa: BLE001
        return None
