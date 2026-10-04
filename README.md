# xsmarts-autoconf

**Find out what your cheminformatics library actually does with SMARTS and SMIRKS.**

SMARTS and SMIRKS look standardized, but libraries disagree:
- on what `r6` or `R3` means;
- on whether `[N+:1]>>[N:1]` removes the charge;
- on whether a cleavage returns one object or two, and whether water and formaldehyde are dropped;
- on what explicit hydrogens do to an edit;
- and on dozens more details.

These differences also change between library versions.

`xsmarts-autoconf` works like `autoconf`, but for chemistry. It runs a
catalog of small, focused, executable examples against whichever library
versions you have installed. It records each library's behavior as a set of
**feature flags**, and it checks the results into a versioned config file.
A differential **fuzzer** shares that catalog. It looks for divergences the
catalog doesn't know about yet, while steering around the ones it already knows.

```
new library version ─▶ xsmarts-autoconf check / update ─▶ configs/<lib>/<version>.json
                                                       ─▶ emulation, translation, warnings, tests
```

The catalog currently has **83 flags** probed across RDKit, chematic, Open
Babel, CDK, Ambit, BioTransformer and two reference engines. See
[docs/NEW_BEHAVIORS.md](docs/NEW_BEHAVIORS.md) for the divergences found while
building it, and [docs/REPORT.md](docs/REPORT.md) for the full per-flag report.

## Install

```bash
pip install xsmarts-autoconf                 # core: lark + hypothesis
pip install "xsmarts-autoconf[rdkit]"        # plus any libraries you want probed
pip install "xsmarts-autoconf[all]"          # rdkit, chematic, openbabel, jpype1
```

Nothing is version-pinned, on purpose: the tool probes **whatever versions
you have installed**. Every chemistry library is an optional import. Missing
libraries are reported and skipped, never errors. RDKit is recommended even
when you aren't probing it, because it serves as the neutral SMILES
normalizer and as the fuzzer's reference for derived features.

| Adapter | Needs | Notes |
|---|---|---|
| `rdkit` | `rdkit` | option `use_chirality=true` |
| `chematic` | `chematic` | |
| `openbabel` | `openbabel` | |
| `cdk` | `jpype1`, a JDK, the BioTransformer 3.0 jar | CDK `SmartsPattern` for matching, Ambit `SMIRKSManager` for apply |
| `biotransformer` | same as `cdk` | BioTransformer's own Java metabolite pipeline |
| `pyref` | `chematic` (for aromaticity) | bundled pure-Python XSMARTS reference engine |
| `xenosmarts` | the `xenosmarts` Python module | installed separately; no compiled wheels ship here |

Environment variables:

| Variable | Purpose |
|---|---|
| `XSMARTS_BIOTRANSFORMER_JAR` | path to `BioTransformer3.0.jar` (bundles CDK + Ambit) |
| `XSMARTS_BIOTRANSFORMER_RUN` | BioTransformer working directory (default: the jar's folder) |
| `JAVA_HOME` | JDK to load (default: JPype's default JVM) |
| `XSMARTS_XENOSMARTS_PATH` | directory containing the `xenosmarts` module, if not installed |
| `XSMARTS_CONFIG_DIR` | where configs are read and written (default: bundled `data/configs`) |
| `XSMARTS_FINDINGS_DIR`, `XSMARTS_FUZZ_DB` | fuzzer output and Hypothesis database |

## Quick start

```bash
xsmarts-autoconf libs                   # what's installed, versions, config status
xsmarts-autoconf check                  # installed versions vs checked-in configs
xsmarts-autoconf update rdkit           # write/refresh the config for your installed RDKit
xsmarts-autoconf matrix                 # all flags side by side
xsmarts-autoconf report --out REPORT.md
xsmarts-autoconf target chematic --like rdkit   # test cases that move chematic to rdkit's behavior
```

`check` reports one status per installed library:

- **ok:** the installed version behaves exactly as its config says.
- **changed:** a flag whose rule didn't change now gives a different result. The library's behavior changed; bump or investigate.
- **stale:** rules were added or edited since the config was written. Run `update`.
- **missing:** no config exists for this version yet. Run `update` and commit it.

Configs are kept **per library version** (`data/configs/<adapter>/<version>.json`).
Each flag entry stores the hash of the rule that produced it, so configs for
older versions are flagged as stale whenever the suite grows. Refresh them
whenever you have that version installed. The test suite
(`pytest`) runs the same check for every installed library.

## How it works

### Rules: one feature flag per file

`src/xsmarts_autoconf/data/rules/<area>/<flag>.json`:

```json
{
 "flag": "match.ring_size_semantics",
 "summary": "`r<n>`: smallest ring is n vs member of any ring of size n",
 "values": {"smallest_ring": "Daylight/RDKit: SSSR smallest ring size",
            "any_ring": "member of any ring of size n (Open Babel)"},
 "cases": [
  {"id": "r6_hydrindane", "op": "match", "query": "[r6]", "mol": "C1CCC2CCCC2C1",
   "orderings": 6, "expect": {"smallest_ring": "match:4", "any_ring": "match:6"}}
 ],
 "provenance": {"discovered": "where and when it was first seen", "refs": []},
 "processing": "pre/post-processing needed to reproduce (AddHs, sanitize, H mode)",
 "fuzz": {"avoid": [["prim.ring_size_r", "mol.fused_ring"]]}
}
```

- **Ops:** `parse`, `match` (unique atom-set matches) and `apply` (SMIRKS).
- **Apply views:** `products` (raw edit), `sanitized` (the library's own sanitizer), `count` (number of outcomes) and `objects` (product objects per outcome: one disconnected object vs separate fragments).
- **Case options:**
  - `explicit_h` adds explicit hydrogens before the op.
  - `orderings: N` / `spellings: [...]` observe the same molecule written in other atom orders and report the set of outcomes. This makes non-unique perception (SSSR, site choice) deterministic, and order dependence visible.
  - `fixed_spelling` marks a case whose spelling is the point.
- **Expectations:** an exact observation (`match:3`, `products:CC=O`, `error`, `unsupported`), `*`, `match:+`, `re:<regex>`, or a list of alternatives.
- **Resolution:** a library gets the value whose expectations all its cases satisfy. `UNKNOWN` means new behavior (add a value). `AMBIGUOUS` means add a distinguishing case.

### Adapters: a thin layer per library

```python
from xsmarts_autoconf.adapter import Adapter

class MyLib(Adapter):
    name = "mylib"
    def version(self): ...
    def parse(self, smarts): ...                          # raise on rejection
    def match(self, smarts, smiles, explicit_h) -> int:   # unique atom-set matches
    def apply(self, smirks, smiles, explicit_h):          # per outcome: [product SMILES, ...]
    def sanitize(self, smiles) -> str | None:             # library-native; None = rejected
```

Override only what the library supports; the rest reports `unsupported`.
Error capture, SMILES normalization and the comparable observation strings
are all handled by the base class. Register the class in `ADAPTERS`
(`adapters.py`).

### Fuzzer

`xsmarts-autoconf sweep A B` runs Hypothesis-based differential fuzzing between two adapters:

- Known divergences between the two libraries are excluded while examples are being *built*, using each rule's `fuzz.avoid` feature conjunctions. Any disagreement that remains is new.
- Three generators:
  - feature-tagged query and edit recipes;
  - corpus-guided (molecules the template actually hits);
  - **molecule-first** (draw a molecule, then write a query from facts that are true about a path in it).
- Findings are shrunk to a minimal example, written as readable JSON, and attributed to rules. An empty attribution means **NEW**.
- `xsmarts-autoconf flipcheck A B` is the self-test. It pretends A has B's value for each divergent flag; the fuzzer must rediscover it.

### Round trip

Engines that can be configured from flags (`pyref`, `xenosmarts`) are checked with
`xsmarts-autoconf roundtrip --blinded 20`:

- **Unblinded:** set each flag, run its rule, and expect the value back.
- **Blinded:** draw random engine settings, run every rule, and compare. This catches coupled flags.

### Comparison website

`xsmarts-autoconf site --out _site` builds a static page from the stored
configs: pick any library versions to compare side by side, or a single
library to see which others share each behavior. The selection, filters and
expanded rows live in the query string, so every view is a shareable link.
`.github/workflows/pages.yml` publishes it to GitHub Pages on every push to
`main` that touches rules, configs or the site. Enable Pages with source
"GitHub Actions" in the repository settings. To preview locally:
`python -m http.server -d _site`.

Colors:

- **Red:** an error, silent failure or corrupted product. These values are listed in `data/site/severity.json`. Relying on an arbitrary SSSR choice instead of a unique ring set counts as a bug, not a policy.
- **Orange:** a valid but different policy or semantics (valence, filtering, output form). Users could be surprised by it.
- **Green:** the behavior most libraries share. Each library gets one vote, bug values never win, and BioTransformer's CDK matcher votes with CDK.

Mark a new bug value in `severity.json` when you add a flag. The reference
engines (`pyref`, `xenosmarts`) are left out by default (`--include-reference`).

## XSMARTS

The bundled grammar and reference engine (`xsmarts_autoconf.xsmarts`) parse
**XSMARTS**: the superset of OpenSMARTS and the RDKit, CDK, chematic and Open
Babel dialects. It builds a typed QueryMol where dialect-dependent spellings
(such as hybridization `^n`) stay unbound until a dialect is chosen.

## Contributing

Contributions are very welcome, especially from people who know a library's
corners.

- **New flags.** Found a library doing something surprising? Add a rule file with the smallest cases that separate the behaviors, a value per behavior, provenance (library, version, where you saw it) and `fuzz.avoid` tags. Run `xsmarts-autoconf matrix` and `xsmarts-autoconf stability`, then `update` and commit the configs for the versions you have.
- **Configs for other versions.** Install an older or newer version of a library, run `xsmarts-autoconf update <lib>`, and send the new `data/configs/<lib>/<version>.json`. This is how the version history grows.
- **New harnesses.** Adapters for other toolkits (Indigo, OpenEye, ChemAxon, Ambit standalone, CDK from Maven, Java and JS libraries...) are a small class each; see above. Generators and feature tags in `gen.py` are welcome too.
- **Fuzz findings.** Run `xsmarts-autoconf sweep A B` on pairs you care about. Each `NEW` finding is a candidate flag.

Please keep flags about *observable behavior*: one question per flag, the
smallest cases that answer it, and expectations that don't depend on SMILES
spelling (outputs are canonicalized).

## Development

```bash
git clone <repo> && cd xsmarts-autoconf
pip install -e ".[all,test]"
pytest -q                     # library-dependent tests skip when a library is missing
```

Layout: `src/xsmarts_autoconf/` (package; `data/rules`, `data/configs` and
`data/findings` are package data), `tests/`, `docs/` (reports and the
behavior log), `.xsmarts-fuzz-db/` (Hypothesis database for the checked-in
findings).
