# autoconf: SMARTS / SMIRKS behavior prober

An autoconf-style prober that pins down how each cheminformatics library
handles SMARTS matching and SMIRKS application. A differential fuzzer
alongside it looks for divergences the catalog doesn't cover yet.

```
new library version -> autoconf -> configs/<lib>/<version>.json (checked in)
                    -> emulation / translation / warnings driven by the config
```

Uses the parent repo's `.venv` and `scripts/smarts_grammar`. Run from this
directory: `../.venv/bin/python -m autoconf <command>`.

## Layout

| Path | What |
|---|---|
| `rules/<area>/<flag>.json` | One feature flag per file: values, executable cases, expected outcomes, provenance, pre/post-processing notes, fuzz tags. **Source of truth; edit by hand.** |
| `configs/<adapter>/<version>[+opts].json` | Autoconf output: resolved value per flag plus every raw observation. |
| `findings/<A>__<B>/<hash>.json` | Fuzzer findings: minimal example, observations, features, attribution. |
| `fuzz-db/` | Hypothesis example database (replays past failures first). |
| `NEW_BEHAVIORS.md` | Divergences found by this work that weren't documented before. |
| `REPORT.md` | `autoconf report` output for the current configs. |
| `autoconf/adapter.py` | `Adapter` base and observation model (all shared logic). |
| `autoconf/adapters.py` | rdkit, chematic, openbabel, cdk (SmartsPattern + Ambit), biotransformer (Java pipeline), pyref (`smarts_grammar`), xenosmarts (Rust engine). |
| `autoconf/rules.py`, `run.py` | Rule loading and value resolution; config writer. |
| `autoconf/gen.py`, `fuzz.py` | Feature-tagged generators; differential fuzzer. |
| `autoconf/roundtrip.py` | Config → configured engine → autoconf round trip. |
| `autoconf/condense.py` | Report and targeted test cases. |

## Commands

```bash
python -m autoconf matrix [--write]              # all adapters, flag table; --write updates configs/
python -m autoconf run rdkit -o use_chirality=true   # one adapter, with key options
python -m autoconf stability [-n 8]              # flakiness: repeats + systematic re-orderings
python -m autoconf report --out REPORT.md        # condensed per-flag explanation and examples
python -m autoconf target chematic --like rdkit  # tests that move chematic to rdkit's behavior
python -m autoconf fuzz rdkit chematic           # one differential search; writes findings/
python -m autoconf sweep rdkit chematic          # multi-seed baseline; must be clean before flipcheck
python -m autoconf flipcheck rdkit chematic      # fuzzer self-test (below)
python -m autoconf roundtrip --blinded 20        # engine round trip
../.venv/bin/python -m pytest tests -q
```

## Adapters

An adapter overrides at most four methods and returns native results:

```python
class MyLib(Adapter):
    name = "mylib"
    def version(self): ...
    def parse(self, smarts): ...                          # raise on rejection
    def match(self, smarts, smiles, explicit_h) -> int:   # unique atom-set matches
    def apply(self, smirks, smiles, explicit_h):          # per outcome: [product SMILES, ...]
    def sanitize(self, smiles) -> str | None:             # lib-native; None = rejected
```

`Adapter.observe` handles everything else: error capture, `Unsupported`, SMILES
normalization (RDKit canonical with sanitize off; `[C]`-style H labels are
kept because they are chemistry), and the comparable observation string:
`ok`, `error`, `unsupported`, `match:N`, `products:A|B`, `outcomes:N`,
`objects:A + B`.

Key options (`-o k=v`) are part of the config identity, e.g. RDKit
`use_chirality=true` flips `match.atom_chirality` to `enforced`.

## Rule files

```json
{
 "flag": "match.ring_size_semantics",
 "summary": "`r<n>`: smallest ring is n vs member of any ring of size n",
 "values": {"smallest_ring": "...", "any_ring": "..."},
 "cases": [
  {"id": "r6_hydrindane", "op": "match", "query": "[r6]", "mol": "C1CCC2CCCC2C1",
   "orderings": 6,
   "expect": {"smallest_ring": "match:4", "any_ring": "match:6"}}
 ],
 "provenance": {"discovered": "...", "refs": ["docs/..."]},
 "processing": "pre/post-processing needed to reproduce (AddHs, sanitize, ...)",
 "fuzz": {"avoid": [["prim.ring_size_r", "mol.fused_ring"]]}
}
```

- **Case fields:**
  - `op`: parse | match | apply.
  - `explicit_h`: AddHs before the op.
  - `view` (apply only): `products` (raw edit), `sanitized` (lib-native sanitizer), `count` (number of outcomes) or `objects` (product objects per outcome, which shows one disconnected object vs separate fragments).
  - `orderings: N`: also observe on N systematic re-orderings of the molecule (rooted at each atom, then reversed numbering) and report the outcome set `a / b`. Use it for perception with several valid answers (non-unique SSSR, site choice).
  - `spellings: [...]`: explicit alternative spellings, for a known order dependence.
  - `fixed_spelling`: the spelling is the point of the case; the stability check won't reorder it.
- **Expectations:** an exact observation, `*`, `match:+`, `re:<regex>`, or a list of alternatives. A value is selected when every case satisfies it. Otherwise the result is `UNKNOWN` (new behavior; add a value) or `AMBIGUOUS:a|b` (add a distinguishing case).
- **`fuzz.avoid`:** a list of *conjunctions* of generator features. The fuzzer excludes them when this flag is a known divergence for the pair, and uses them to attribute findings.

## Fuzzer

Hypothesis-based differential fuzzing between two adapters (`find`, so every
finding is shrunk; database in `fuzz-db/`; readable JSON in `findings/`).

- **Known divergences are avoided while building examples.** Flags whose configured values differ between A and B contribute their `fuzz.avoid` conjunctions. Single features drop vocabulary items before drawing; conjunctions with the op resolve up front; the rest are filtered after drawing.
- **Three generators:**
  - query/recipe-first (feature-tagged atoms, bonds, edit recipes);
  - corpus-guided (the molecule is drawn mostly from those the template actually hits);
  - **molecule-first** (draw a molecule, then build a query from primitives that are true for a path in it).
- **Derived features** come from RDKit as a neutral reference: `sites.multiple`, `sites.ordered_multiple`, `outcome.valence_invalid`.
- **Focus bias** toward vocabulary any rule has ever named. This is blind to which flag is under test.
- **Attribution:** `explained_by` lists the pair's divergent flags whose conjunction the example carries. Empty means **NEW**.

**`flipcheck`** is the key self-test. For each flag where A and B differ, it
pretends A has B's value and fuzzes; the shrunk example must carry that flag's
features. `MASKED` means another divergent flag avoids the same features.
Run `sweep` first: residual baseline findings mask everything else.

## Round trip

`roundtrip.py` drives engines that are configurable from flags (`PyRef`,
`Xenosmarts`; wiring tables `PYREF_FLAGS`, `XENOSMARTS_FLAGS` in
`adapters.py`):

- **Unblinded:** per flag and value, configure that flag, run its rule, and expect the value back.
- **Blinded:** draw engine settings with Hypothesis, run all rules, and compare all wired flags. This finds coupled flags. Declared implications live in `roundtrip.IMPLIES`.

## Workflow for a new library version

1. `python -m autoconf matrix --write`: a new version writes a new config file.
2. `UNKNOWN` / `AMBIGUOUS`: add a value or a distinguishing case to the rule.
3. `python -m autoconf stability`: fix flaky cases (`orderings`, `spellings`, `fixed_spelling`).
4. `sweep A B` for the pairs you care about. For each NEW finding, add a rule or extend one (and its `fuzz.avoid`), then repeat until clean.
5. `flipcheck A B` and `pytest`.
