# New behavior divergences found by autoconf (2026-10-03)

These are divergences **not documented before this work** in `docs/smirks/*`,
`docs/smarts_dialects.md`, `docs/chematic/*` or `docs/xenosmarts/AMBIT.md`.
Each one is an executable flag. The rule file holds the minimal cases,
expected outputs per value and provenance. The per-library values are in
`configs/<adapter>/<version>.json`.

Versions: rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1 with
Ambit (BioTransformer jar), biotransformer = BioTransformer's Java
`generateAllMetabolitesFromAtomContainer` pipeline, pyref = `scripts/smarts_grammar`
reference matcher plus Ambit-style processor.

All paths are relative to `autoconf/`. "How found": **matrix** = discovery
matrix, **stability** = systematic re-ordering check, **fuzz** = differential
fuzzer (finding JSON under `findings/`).

## SMARTS matching

| Flag (rule file) | New behavior | How found |
|---|---|---|
| `match.ring_count_basis` (`rules/match/ring_count_basis.json`) | `R<n>` on cages: RDKit and pyref use a symmetrized ring set (cubane `[R3]` = 8, adamantane `[R3]` = 4, bicyclo[2.2.2]octane `[R2]` = 6, norbornane `[R2]` = 4). Chematic, OB and CDK use SSSR (4 / 1 / 4 / 3). Counts are stable over 12 re-orderings on every engine. | matrix |
| `match.ring_size_semantics` (`rules/match/ring_size_semantics.json`) | **Open Babel** `r<n>` = member of *any* ring of size n (hydrindane `[r6]` = 6; spiro). RDKit, Chematic and CDK use the smallest ring (4). pyref's default (any) matches OB, not RDKit. | matrix |
| `match.unspecified_isotope` | **Chematic ignores isotope primitives**: `[12C]` matches unlabeled carbon, and `[13C]` matches both carbons of `[13CH3]C`. | matrix, refined by flipcheck |
| `match.implicit_h_lowercase_h` | Chematic and OB: bare `[Ch]` does not match CH3 (Daylight: at least one implicit H). | matrix |
| `match.proton` | Chematic, OB and pyref: `[H+]` does not match a bare proton `[H+]`. | matrix |
| `match.h_atom_query` | OB matches `[C][H]` against **implicit** H (4 on methane, no AddHs). Chematic never matches bracket `[H]` as an atom, even after AddHs (`[#1]` works). | matrix |
| `match.atom_chirality` | OB, CDK and the BT gate enforce `@`/`@@` (an unspecified-stereo molecule fails). RDKit (default), Chematic and pyref ignore them. | matrix |
| `match.bond_stereo` | **Chematic bug:** a `/` or `\` inside a branch on the first stereo atom is read inverted. `C(/F)=C/F` (cis) matches `F/C=C/F`, and `C(/F)=C\F` (trans) doesn't. CDK enforces stereo; RDKit, OB and pyref ignore it. | stability |

## SMARTS syntax surface

| Flag | New behavior |
|---|---|
| `syntax.hybridization` | Chematic accepts `^6`/`^7` (docs say `^0`–`^5`). CDK rejects `^0`, and `^3` never matches because SmartsPattern atoms aren't hybridization-typed. OB bare `^` matches sp carbon. pyref parses `^n` but can't match it. |
| `syntax.insaturation_i` | Chematic parses `i1` but it matches nothing. |
| `syntax.range_counts` | CDK (jar) accepts `{lo-hi}` ranges. |
| `syntax.component_grouping` | OB parses `(C).(O)` and **ignores** the grouping. CDK enforces it. RDKit, Chematic and pyref reject it. |
| `syntax.dot_disconnected` | OB rejects an ungrouped `C.O` query. |
| `syntax.ring_size_k` | OB and CDK reject `k<n>`. |
| `syntax.periodic_group_G` | CDK SmartsPattern in the BT jar rejects `G16` (only pyref accepts). |
| `syntax.aliphatic_any_A`, `syntax.aromatic_selenium`, `syntax.unclosed_ring` | pyref rejects `[A]` and `[se]`, and accepts an unclosed ring `C1CC`. |

## SMIRKS apply (edit semantics)

| Flag | New behavior | How found |
|---|---|---|
| `smirks.charge_hcount` | Setting ±1 on a neutral atom: RDKit uses the valence rule (`[CH2+]C`). **Chematic adds H to cations** (`C[CH4+]`). **BioTransformer keeps the H count** (`C[CH3+]`, `CC[OH-]`). **OB charges every matching site** (`[CH2+][CH2+]`). | fuzz (`findings/rdkit__chematic/01361e5f50.json`) |
| `smirks.neutralize_written_charge` | `[N+:1]>>[N:1]`: **RDKit keeps the +1** (product charge unwritten, so the reactant charge is inherited). BioTransformer gives `C[NH3]` (neutral, H kept). | matrix |
| `smirks.unwritten_charge` | `[N:1]>>[N:1]` on `C[NH3+]`: Chematic **resets the charge** to 0. | matrix |
| `smirks.product_h_pin` | RDKit treats product H as authoritative (`[CH2]C`), and with AddHs adds on top (`C[CH5]`). Chematic returns nothing. pyref and BioTransformer ignore it. | matrix |
| `smirks.hcount_query_explicit_h` | RDKit `[CH3:1]>>[CH3:1]` with AddHs gives `C[CH6]`. | matrix |
| `smirks.product_h_atom_added` | `[O:1]>>[O:1][H]` on an alkoxide: RDKit drops the product `[H]` atom. Chematic protonates and resets the charge (`CCO`). pyref and BioTransformer give `CC[OH-]`. | matrix |
| `smirks.undefined_product_bond` | `=,:` on a product bond: RDKit applies the first alternative (`C=C`). OB and pyref skip the bond edit. Chematic rejects. (The CDK adapter rejects because it raises on SMIRKSManager errors; BT's A6b partial apply isn't reached on this path.) | matrix |
| `smirks.fragmented_reactant` | RDKit runs a `[C:1].[O:2]` reactant as two templates on two copies of the molecule (`COCO`, intermolecular). | matrix |
| `smirks.product_only_map` | RDKit and Chematic create a product-only mapped atom; the others reject. | matrix |
| `smirks.outcome_multiplicity` | RDKit returns every *ordered* mapping (2 for C–C, 8 for cyclobutane ring opening). Chematic de-duplicates identical products (2 vs 3 outcomes for `[*:1]>>[*:1]` on ethanol). | matrix |
| `smirks.multi_site_application` | **OB transforms all sites in one product** (`[O-]CC[O-]` from ethylene glycol). BioTransformer merges sites into one fragment set. | fuzz (rdkit vs openbabel) |
| `smirks.site_choice_order_dependence` | Results depend on input atom order. Chematic and OB: symmetric `[C:1][C:2]>>[C:1]` on ethanol gives `C` or `CO` depending on spelling. BioTransformer: which diol OH gets oxidized follows atom order. | stability |
| `smirks.star_on_explicit_h` | Mapped `*` reaches explicit H atoms. RDKit with AddHs gives `CCl|C[H]Cl` (Cl bonded to H). **BioTransformer does this in every run** (its substrate is always explicit-H): `[*:1]>>[*:1]Cl` on methane gives `C[H]Cl`. | fuzz (cdk vs biotransformer) |
| `smirks.aromatic_product` | pyref dearomatizes products (benzene identity gives `C1CCCCC1`), and `[cH:1]` doesn't match benzene. BioTransformer outputs Kekulé with H kept (`O[CH]1=CC=CC=C1`). | matrix |
| `smirks.unmapped_reactant_deleted` | With AddHs, Ambit and pyref leave the deleted atom's H as a separate fragment (`[CH2]C.[H]`). | matrix |
| `smirks.h_atom_in_template` | Ambit with AddHs doesn't refill H after deleting `[H]` (`[CH3]`). OB and BioTransformer match `[H]` against implicit H. | matrix |
| `smirks.recursive_in_reactant`, `smirks.nested_recursive` | OB rejects `$()` in SMIRKS; Chematic rejects nested `$()`. | matrix |
| `smirks.add_unmapped_atom`, `smirks.edits_with_explicit_h`, `smirks.valence_invalid_raw`, `smirks.sanitize_policy` | **BioTransformer never adjusts explicit H after an edit**: `CC[OH]C`, `C[CH2]=[OH]`, `CO=[CH3]`, `CN(C)=[CH3]`. Real BT rules must delete `[H]` explicitly. | matrix (biotransformer adapter) |
| `smirks.sanitizer` | pyref has no product sanitizer. | fuzz (rdkit vs pyref) |

## Product handling (cleavage, byproducts)

| Flag | New behavior |
|---|---|
| `products.fragment_objects` | Cleavage output shape. RDKit and Chematic return **one object per product-template component** (`CC(=O)O + CCO`). Ambit (raw) and pyref return **one disconnected object** (`CC(=O)O.CCO`). BioTransformer **splits into fragments and merges all sites into one de-duplicated set** (`[C:1]O[C:2]>>[C:1].[C:2]` on diethyl ether gives one `CC`; chain scission of butane gives `C + CC + CCC`). Every engine keeps both fragments unless filtered. |
| `products.grouped_product_component` | RDKit honors product grouping `([C:1].[O:2])` as one object; BioTransformer splits it anyway; Chematic and pyref reject it. |
| `products.byproduct_filter` | Only BioTransformer drops small byproducts: H₂O, NH₃, HCl and formaldehyde (O-demethylation leaves only the alcohol). Methanol and acetic acid are kept. |
| `products.new_double_bond_h` | BioTransformer leaves H on atoms that gain a double bond: N-deethylation gives `C[CH2]=O`, decarboxylation gives `O=C=[OH]`. That malformed CO₂ escapes the CO₂ blocklist. pyref emits dummies. |

## Added after the first write-up (same day)

| Flag (rule file) | New behavior | How found |
|---|---|---|
| `smirks.stereo_carried` | **Chematic flips tetrahedral parity** on a stereocenter next to the mapped atom when the map is on a particular neighbor: `[CH3:1]>>[C:1]` on `C[C@H](N)O` gives `C[C@@H](N)O`; mapping the O neighbor preserves it. BioTransformer and pyref drop stereo. | fuzz rdkit↔chematic |
| `smirks.reactant_aromaticity` | Aromaticity seen by the SMIRKS reactant matcher. RDKit and pyref perceive Daylight aromaticity. **Chematic `run_smirks` and raw Ambit take the input as written**: Kekulé benzene matches `[C:1]`, and aromatic-spelled 4-pyranone doesn't. BioTransformer uses the CDK model (benzene aromatic, 4-pyranone not; B0). | fuzz rdkit↔chematic |
| `smirks.explicit_h_apply` | With AddHs, Chematic returns nothing even for simple charge edits (`[O:1]>>[O-:1]`). OB, BioTransformer and pyref keep the H count (`CC[OH-]`). | fuzz rdkit↔chematic |
| `smirks.reactant_query_syntax` | Chematic **and Open Babel** reject SMARTS logic in SMIRKS reactants (`;` `,` `X`). This is DISCOVERED_BEHAVIORS C1, rediscovered automatically; OB is new. | fuzz (molecule-first) |
| `match.aromatic_valence` | Chematic counts aromatic bonds as order 1 for `v`: benzene C is `v3`, `[c;v4]` matches nothing. | fuzz (molecule-first) |
| `match.directional_bond` | `/` and `\` without stereo context: RDKit, CDK and BT match single **and aromatic** bonds; OB, pyref and xenosmarts match single only; **Chematic matches nothing** (even `C/C` on ethane). | fuzz rdkit↔openbabel |
| `smirks.multi_site_application` | OB transforms every site in one product (`[O-]CC[O-]`); BT flattens sites. | fuzz rdkit↔openbabel |
| `smirks.new_bond_query_order` (A6) | `[C:1]>>[C:1]~C`: RDKit and Chematic copy the query bond into the product (`CC~C`). Ambit, BT and OB reject it. pyref and xenosmarts add the atom **without the bond** (`C.CC`). | catalog gap probe |
| `smirks.colon_product_bond` (A14) | Product `:` on ethane: RDKit sets aromatic flags (`cc`); Chematic writes an aromatic bond on aliphatic atoms (`C:C`); Ambit, BT, pyref and xenosmarts make no change. | catalog gap probe |
| `smirks.undefined_order_both_sides` (A6b) | `-,:` → `=,:`: RDKit applies `C=C`; Chematic and OB reject; Ambit, BT, pyref and xenosmarts apply it as a no-op. | catalog gap probe |
| `smirks.equivalent_h_mappings` (A11) | The cdk adapter (SMIRKSManager without `FlagFilterEquivalentMappings`) gives one outcome per H atom (4 on methane), like RDKit and Chematic. BT and xenosmarts collapse them to 1. | catalog gap probe |
| `products.validity_filter` (B5a) | BT drops hydroperoxide, ketene and carbon-free fragments (H₂S, HBr), but **keeps the gem-diol `CC(O)O`**, contrary to DISCOVERED_BEHAVIORS B5a (that InValidSMARTS pattern needs explicit `[H]`). | catalog gap probe |
| `smirks.bond_order_decrease_retyping` | C=O → C–O: pyref and **xenosmarts raw apply produce dummies** (`[*H][*H2]C`), while real Ambit raw output (cdk adapter) gives `[C][C][O]` with no dummies. Likely an emulation difference in xenosmarts' A25b rule (dummies on bond-order *decrease*). | fuzz rdkit↔pyref |
| `smirks.mapped_aromatic_nh` | **Chematic drops the H of a mapped aromatic `[nH]`**: identity `[n:1]>>[n:1]` on pyrrole gives `c1ccnc1` (invalid). An unmapped ring N–H is kept. | flipcheck rdkit↔chematic |
| `products.spectator_components` | Untouched components of a multi-component substrate: RDKit and Chematic drop them. OB and xenosmarts return the whole input as one object; BioTransformer keeps them as separate fragments (then the blocklist may drop small ones); Ambit raw keeps them with labels. | sweep rdkit↔xenosmarts |
| `smirks.aromatic_output_form` | Untouched aromatic rings come out Kekulé from BioTransformer and xenosmarts (`CC1=CC=CC=C1`), aromatic from RDKit and Chematic. | sweep rdkit↔xenosmarts |
| `match.count_semantics` | xenosmarts `Matcher.count()` counts ordered mappings (`CC` on ethane = 2, benzene ring = 12); all libraries count unique atom sets. | sweep rdkit↔xenosmarts |
| `match.substituted_aromatic_perception` | pyref errors on every non-benzene aromatic (toluene, pyridine, anisole). | fuzz rdkit↔pyref |

## For the xenosmarts agent

- `Matcher.count()` counts **ordered mappings**, not unique atom sets (`F/C=C/F` → 2, `C/C` on ethane → 2). The autoconf adapter can't de-duplicate without a mapping list or a unique count from the API, so `match.bond_stereo` is `UNKNOWN` for xenosmarts.
- Round trip (`python -m autoconf roundtrip --blinded 24`) passes for all 5 profile flags, with one coupling found and declared: `kekule_match=True` implies Kekulé comparison inside compound bonds (`compound_bond_kekule` reads `kekule_order` regardless).
- `bond_order_decrease_retyping` above is the one place xenosmarts' raw apply differs from real Ambit raw output.

## For the pyref / smarts_grammar owner

- Round trip: `double_excludes_aromatic=False` makes `=` match aromatic bonds **only when the molecule was written Kekulé** (`C1=CC=CC=C1`: 3 matches; `c1ccccc1`: 0). Recorded as `match.double_bond_vs_aromatic = kekule_input_only`.
- pyref errors on any non-benzene aromatic (toluene, pyridine, anisole) and dearomatizes products.

## Not yet captured as a flag

- pyref raises on `[R2]` against pyrene: a case of `match.substituted_aromatic_perception`.
- **Environment, not a library:** at 18:01 on 2026-10-03, `scripts/smarts_grammar/grammars/opensmarts.lark` was modified and `build_querymol('c=c', ...)` now returns zero atoms. pyref results after that time are invalid; `tests/test_autoconf.py::test_committed_config_reproduces[pyref/...]` flags it.
- BioTransformer drops ethene from `[C:1]-[C:2]>>[C:1]=[C:2]` on ethane (no product; likely the validity filter). It's folded into `smirks.edits_with_explicit_h` and `smirks.outcome_multiplicity` as accepted observations, not isolated.

## For the feature prober

The machine-readable source of truth is `rules/**.json` (flag, values, cases,
provenance). Per-engine resolved values plus raw observations are in
`configs/<adapter>/<version>.json`. `python -m autoconf matrix` prints the table.
