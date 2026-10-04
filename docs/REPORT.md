# Autoconf report

| adapter | version | options | rules digest |
|---|---|---|---|
| rdkit | 2026.03.6 |  | 6c530e61e71f8019 |
| chematic | 1.0.30 |  | 6c530e61e71f8019 |
| openbabel | 3.2.1 |  | 6c530e61e71f8019 |
| cdk | 2.7.1+ambit(bt-jar) |  | 6c530e61e71f8019 |
| biotransformer | 2.7.1+biotransformer(fat-jar) |  | 6c530e61e71f8019 |
| pyref | xsmarts-0.1.0 |  | 6c530e61e71f8019 |
| xenosmarts | local-build |  | 6c530e61e71f8019 |

## Flag values

| flag | rdkit | chematic | openbabel | cdk | biotransformer | pyref | xenosmarts |
|---|---|---|---|---|---|---|---|
| `match.aromatic_valence` **≠** | kekule_total | aromatic_bond_as_one | kekule_total | kekule_total | kekule_total | kekule_total | kekule_total |
| `match.aromaticity_exocyclic_carbonyl` | daylight_like | daylight_like | daylight_like | daylight_like | daylight_like | daylight_like | daylight_like |
| `match.atom_chirality` **≠** | ignored | ignored | enforced | enforced | enforced | ignored | ignored |
| `match.bond_stereo` **≠** | ignored | branch_direction_inverted | ignored | enforced | enforced | ignored | ignored |
| `match.compound_bond_kekule` | aromatic_aware | aromatic_aware | aromatic_aware | aromatic_aware | aromatic_aware | aromatic_aware | aromatic_aware |
| `match.count_semantics` **≠** | unique_atom_sets | unique_atom_sets | unique_atom_sets | unique_atom_sets | unique_atom_sets | unique_atom_sets | ordered_mappings |
| `match.degree_with_explicit_h` | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms |
| `match.directional_bond` **≠** | single_or_aromatic | never_without_stereo | single_only | single_or_aromatic | single_or_aromatic | single_only | single_only |
| `match.double_bond_vs_aromatic` | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic |
| `match.h_atom_query` **≠** | explicit_only | bracket_h_not_atom | implicit_matchable | explicit_only | explicit_only | explicit_only | explicit_only |
| `match.h_count_with_explicit_h` | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms | counts_h_atoms |
| `match.implicit_h_lowercase_h` **≠** | at_least_one | no_match | no_match | at_least_one | at_least_one | at_least_one | at_least_one |
| `match.nested_recursive` | evaluated | evaluated | evaluated | evaluated | evaluated | evaluated | evaluated |
| `match.or_with_any_atom` **≠** | correct | correct | correct | drops_any | drops_any | correct | correct |
| `match.proton` **≠** | matches | no_match | no_match | matches | matches | no_match | no_match |
| `match.ring_count_basis` **≠** | symmetric | sssr | sssr | sssr | sssr | symmetric | symmetric |
| `match.ring_size_semantics` **≠** | smallest_ring | smallest_ring | any_ring | smallest_ring | smallest_ring | any_ring | any_ring |
| `match.single_bond_vs_aromatic` | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic | excludes_aromatic |
| `match.substituted_aromatic_perception` **≠** | ok | ok | ok | ok | ok | error | ok |
| `match.unspecified_isotope` **≠** | natural_is_unspecified | isotope_ignored | natural_is_unspecified | natural_is_unspecified | natural_is_unspecified | natural_is_unspecified | natural_is_unspecified |
| `products.byproduct_filter` **≠** | kept | kept | rejected | kept | blocklist | kept | kept |
| `products.fragment_objects` **≠** | per_template_component | per_template_component | rejected | single_object | split_flattened | single_object | single_object |
| `products.grouped_product_component` **≠** | one_object | rejected | rejected | one_object | ignored_split | one_object | rejected |
| `products.new_double_bond_h` **≠** | h_adjusted | h_adjusted | rejected | dummies | h_kept_overvalent | dummies | dummies |
| `products.spectator_components` **≠** | dropped | dropped | kept | kept_labels | kept_split | kept | kept |
| `products.validity_filter` **≠** | kept | kept | kept | kept | bt_invalid_dropped | kept | kept |
| `smirks.add_atom_with_explicit_h` **≠** | h_aware | empty | rejected | untyped | h_not_adjusted | h_not_adjusted | h_not_adjusted |
| `smirks.add_unmapped_atom` **≠** | added | added | rejected | untyped | h_kept_overvalent | added | added |
| `smirks.aromatic_output_form` **≠** | aromatic | aromatic | rejected | kekule_labels | kekule | rejected | kekule |
| `smirks.aromatic_product` **≠** | aromatic_preserved | aromatic_preserved | rejected | kekule_labels | kekule_h_kept | dearomatized | kekule_output |
| `smirks.bond_order_decrease_retyping` **≠** | retyped | retyped | retyped | labels | retyped | dummies | dummies |
| `smirks.charge_hcount` **≠** | valence_rule | cation_adds_h | all_sites_in_place | untyped | h_count_kept | valence_rule | valence_rule |
| `smirks.charge_plus2_hcount` **≠** | valence_reduced | h_added | valence_reduced | untyped | valence_reduced | h_cleared | h_cleared |
| `smirks.colon_product_bond` **≠** | aromatic_flag_set | aromatic_bond_written | labels | labels | no_change | no_change | no_change |
| `smirks.delete_mapped_by_omission` **≠** | deleted | deleted | deleted_no_refill | rejected | rejected | rejected | rejected |
| `smirks.disconnect` **≠** | split | split | rejected | labels | split_deduped | split | split |
| `smirks.edits_with_explicit_h` **≠** | h_aware | empty | h_not_adjusted | untyped | h_kept_overvalent | untyped | untyped |
| `smirks.element_change` **≠** | applied | ignored | corrupt | rejected | rejected | rejected | rejected |
| `smirks.equivalent_h_mappings` **≠** | per_h_atom | per_h_atom | single_application | per_h_atom | collapsed | per_h_atom | collapsed |
| `smirks.explicit_h_apply` **≠** | h_aware | edits_empty | h_kept | untyped | h_kept | h_kept | h_kept |
| `smirks.fragmented_reactant` **≠** | intermolecular_pair | rejected | rejected | rejected | rejected | rejected | rejected |
| `smirks.h_atom_in_template` **≠** | explicit_only | explicit_only | implicit_matchable | explicit_only_no_refill | implicit_matchable | explicit_only | explicit_only |
| `smirks.hcount_query_explicit_h` **≠** | pin_adds_h | empty | rejected | preserved | preserved | preserved | preserved |
| `smirks.identity_labels` **≠** | organic | organic | rejected | labels_need_explicit_h | organic | organic | organic |
| `smirks.mapped_aromatic_nh` **≠** | preserved | h_lost_when_mapped | rejected | labels | kekule | dearomatized | kekule |
| `smirks.multi_site_application` **≠** | per_site | per_site | all_sites_in_place | per_site | flattened_h_kept | per_site | per_site |
| `smirks.nested_recursive` **≠** | evaluated | rejected | rejected | always_true | always_true | evaluated | always_true |
| `smirks.neutralize_written_charge` **≠** | inherited | neutralized | neutralized | untyped | neutralized_h_kept | neutralized | neutralized |
| `smirks.new_bond_query_order` **≠** | query_bond_copied | query_bond_copied | rejected | rejected | rejected | bond_dropped | bond_dropped |
| `smirks.outcome_multiplicity` **≠** | all_mappings | deduped_products | single_application | unique_atom_sets | flattened | unique_atom_sets | unique_atom_sets |
| `smirks.product_h_atom_added` **≠** | h_dropped | protonated_reset | rejected | untyped | h_added_charge_kept | h_added_charge_kept | h_added_charge_kept |
| `smirks.product_h_pin` **≠** | authoritative | rejected_empty | rejected | labels | ignored | ignored | ignored |
| `smirks.product_only_map` **≠** | created | created | rejected | rejected | rejected | rejected | rejected |
| `smirks.product_plusplus` **≠** | same_as_plus2 | same_as_plus2 | same_as_plus2 | untyped | same_as_plus2 | same_as_plus2 | same_as_plus2 |
| `smirks.reactant_aromaticity` **≠** | daylight_perceived | not_perceived | rejected | not_perceived | cdk_model | daylight_perceived | daylight_perceived |
| `smirks.reactant_query_syntax` **≠** | full_smarts | smiles_only | smiles_only | full_smarts | full_smarts | full_smarts | full_smarts |
| `smirks.recursive_in_reactant` **≠** | supported | rejected | rejected | supported | supported | supported | supported |
| `smirks.sanitize_policy` **≠** | drops_invalid | keeps_hypervalent_n | keeps_all | untyped | h_kept_overvalent | n/a | n/a |
| `smirks.sanitizer` **≠** | native | native | native | native | native | n/a | n/a |
| `smirks.site_choice_order_dependence` **≠** | order_independent | mapping_order_dependent | mapping_order_dependent | order_independent | site_order_dependent | order_independent | order_independent |
| `smirks.star_on_explicit_h` **≠** | h_atoms_when_explicit | explicit_edits_empty | rejected | untyped | always_explicit | h_atoms_no_refill | h_atoms_no_refill |
| `smirks.star_retype` **≠** | keeps_reactant_atom | keeps_reactant_atom | corrupt | rejected | rejected | rejected | rejected |
| `smirks.stereo_carried` **≠** | preserved | flipped_by_neighbor_order | rejected | labels | dropped | dropped | dropped |
| `smirks.undefined_order_both_sides` **≠** | first_alternative | rejected | rejected | noop_applied | noop_applied | noop_applied | noop_applied |
| `smirks.undefined_product_bond` **≠** | first_alternative | rejected | skipped | rejected | rejected | skipped | skipped |
| `smirks.unmapped_reactant_deleted` **≠** | deleted | deleted | rejected | labels_h_orphaned | deleted | deleted_h_orphaned | deleted_h_orphaned |
| `smirks.unwritten_charge` **≠** | inherited | reset | rejected | labels | inherited | inherited | inherited |
| `smirks.valence_invalid_raw` **≠** | kept_raw | dropped_at_apply | hypervalent | untyped | h_kept_overvalent | untyped | untyped |
| `syntax.aliphatic_any_A` **≠** | supported | supported | supported | supported | supported | rejected | supported |
| `syntax.aliphatic_hetero_neighbors_Z` **≠** | supported | rejected | rejected | rejected | rejected | supported | supported |
| `syntax.aromatic_selenium` **≠** | supported | supported | supported | supported | supported | rejected | rejected |
| `syntax.cdk_hash_X` **≠** | rejected | rejected | rejected | supported | supported | supported | supported |
| `syntax.charge_plusplus` | charge2 | charge2 | charge2 | charge2 | charge2 | charge2 | charge2 |
| `syntax.component_grouping` **≠** | rejected | rejected | ignored | enforced | enforced | ignored | rejected |
| `syntax.dative_bond` **≠** | supported | rejected | rejected | rejected | rejected | supported | rejected |
| `syntax.dot_disconnected` **≠** | supported | supported | rejected | supported | supported | supported | supported |
| `syntax.hetero_neighbors_z` **≠** | supported | rejected | rejected | rejected | rejected | supported | supported |
| `syntax.hybridization` **≠** | zero_to_five | lenient_digits | openbabel_bare | cdk_one_based_untyped | cdk_one_based_untyped | unsupported | unsupported |
| `syntax.insaturation_i` **≠** | rejected | parsed_no_match | rejected | supported | supported | supported | supported |
| `syntax.periodic_group_G` **≠** | rejected | rejected | rejected | rejected | rejected | supported | supported |
| `syntax.range_counts` **≠** | supported | rejected | rejected | supported | supported | supported | supported |
| `syntax.ring_size_k` **≠** | supported | supported | rejected | rejected | rejected | supported | supported |
| `syntax.unclosed_ring` **≠** | rejected | rejected | rejected | rejected | rejected | accepted | accepted |

## Divergent flags

### `match.aromatic_valence`

Total valence `v` on aromatic atoms

- **aromatic_bond_as_one** (chematic): aromatic bonds count 1: benzene C is v3 (chematic)
- **kekule_total** (rdkit, openbabel, cdk, biotransformer, pyref, xenosmarts): aromatic C in benzene has v4 (RDKit/Daylight)

Minimal example: `[c;v4]` on `c1ccccc1` [match]: `aromatic_bond_as_one` → `match:0`, `kekule_total` → `match:6`

Discovered: fuzz rdkit vs chematic (molecule-first generator) 2026-10-03

### `match.atom_chirality`

Tetrahedral `@`/`@@` in queries

- **enforced** (openbabel, cdk, biotransformer): chirality must agree; unspecified mol fails
- **ignored** (rdkit, chematic, pyref, xenosmarts): chirality ignored (RDKit default useChirality=False)

Minimal example: `[C@@H](F)(Cl)Br` on `[C@H](F)(Cl)Br` [match]: `enforced` → `match:0`, `ignored` → `match:1`

Processing: RDKit adapter option use_chirality=True switches to enforced.

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.bond_stereo`

Directional bonds `/` `\` in queries

- **branch_direction_inverted** (chematic): enforced, but a `/` `\` inside a branch on the first stereo atom is read inverted (chematic 1.0.30): C(/F)=C/F (cis) matches trans
- **enforced** (cdk, biotransformer): must agree; unspecified mol fails
- **ignored** (rdkit, openbabel, pyref, xenosmarts): cis/trans ignored

Minimal example: `F/C=C/F` on `C(/F)=C/F` [match]: `branch_direction_inverted` → `match:+`, `enforced` → `match:0`

Discovered: autoconf stability check 2026-10-03: chematic result changed under reordered SMILES

### `match.count_semantics`

What a match count counts when one atom set matches in several orders

- **ordered_mappings** (xenosmarts): one per ordered mapping: CC on ethane = 2 (xenosmarts Matcher.count)
- **unique_atom_sets** (rdkit, chematic, openbabel, cdk, biotransformer, pyref): one per atom set (RDKit uniquify, chematic, Open Babel GetUMapList, CDK uniqueAtoms)

Minimal example: `CC` on `CC` [match]: `ordered_mappings` → `match:2`, `unique_atom_sets` → `match:1`

Processing: Adapter contract is unique atom sets; xenosmarts exposes only an ordered count, so this flag records the API semantics.

Discovered: sweep rdkit vs xenosmarts 2026-10-03

### `match.directional_bond`

Directional `/` `\` bonds in a query without stereo context

- **never_without_stereo** (chematic): `/` matches nothing unless stereo is defined, even C/C on ethane (chematic)
- **single_only** (openbabel, pyref, xenosmarts): `/` matches single bonds only (Open Babel, pyref)
- **single_or_aromatic** (rdkit, cdk, biotransformer): `/` matches single and aromatic bonds (RDKit, CDK)

Minimal example: `C/C` on `CC` [match]: `never_without_stereo` → `match:0`, `single_only` → `match:+`

Discovered: fuzz rdkit vs openbabel 2026-10-03

### `match.h_atom_query`

Graph `[H]` atom in a query (`[C][H]`) vs implicit / explicit H

- **bracket_h_not_atom** (chematic): never matches as an atom, even with AddHs (chematic)
- **explicit_only** (rdkit, cdk, biotransformer, pyref, xenosmarts): matches only after AddHs
- **implicit_matchable** (openbabel): matches implicit H too (Open Babel)

Minimal example: `[C][H]` on `C` [match] (explicit H): `bracket_h_not_atom` → `match:0`, `explicit_only` → `match:4`

Processing: explicit_h=True means the adapter adds explicit H to the molecule before matching.

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.implicit_h_lowercase_h`

Bare `h` (implicit H, default at least one)

- **at_least_one** (rdkit, cdk, biotransformer, pyref, xenosmarts): [Ch] matches CH3
- **no_match** (chematic, openbabel): [Ch] does not match implicit-H methyl (chematic, Open Babel)

Minimal example: `[Ch]` on `CC` [match]: `at_least_one` → `match:2`, `no_match` → `match:0`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.or_with_any_atom`

Bare `*` inside a comma-OR

- **correct** (rdkit, chematic, openbabel, pyref, xenosmarts): [*,#7] matches any atom
- **drops_any** (cdk, biotransformer): `*` dropped: [*,#7] == [#7] (CDK SmartsPattern in BT jar, gate path)

Minimal example: `[*,#7]` on `CC` [match]: `correct` → `match:2`, `drops_any` → `match:0`

Processing: Engine config: pyref Profile.or_drops_any

Discovered: BioTransformer gate parity work (AMBIT.md G1)

### `match.proton`

`[H+]` matches a bare proton

- **matches** (rdkit, cdk, biotransformer): proton matched
- **no_match** (chematic, openbabel, pyref, xenosmarts): no match

Minimal example: `[H+]` on `[H+]` [match]: `matches` → `match:1`, `no_match` → `match:0`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.ring_count_basis`

`R<n>` ring-membership count basis on cage systems

- **sssr** (chematic, openbabel, cdk, biotransformer): SSSR (cubane has 5 rings, R3 on 4 atoms)
- **symmetric** (rdkit, pyref, xenosmarts): symmetrized SSSR / relevant cycles (all 8 atoms R3)

Minimal example: `[R3]` on `C12C3C4C1C5C2C3C45` [match]: `sssr` → `match:4`, `symmetric` → `match:8`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.ring_size_semantics`

`r<n>`: smallest ring is n vs member of any ring of size n

- **any_ring** (openbabel, pyref, xenosmarts): member of any (relevant) ring of size n
- **smallest_ring** (rdkit, chematic, cdk, biotransformer): Daylight/RDKit: SSSR smallest ring size

Minimal example: `[r6]` on `C1CCC2CCCC2C1` [match]: `any_ring` → `match:6`, `smallest_ring` → `match:4`

Processing: Engine config: pyref Profile.ring_size_any

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `match.substituted_aromatic_perception`

Molecule preparation for substituted / hetero aromatics

- **error** (pyref): preparation raises for any non-benzene aromatic (pyref perceive)
- **ok** (rdkit, chematic, openbabel, cdk, biotransformer, xenosmarts): toluene, pyridine and anisole prepare and match

Minimal example: `*` on `Cc1ccccc1` [match]: `error` → `error`, `ok` → `match:7`

Discovered: fuzz rdkit vs pyref 2026-10-03

### `match.unspecified_isotope`

Isotope primitives in queries (`[12C]`, `[13C]`)

- **isotope_ignored** (chematic): isotope primitive ignored: [12C] and [13C] match every carbon (chematic 1.0.30)
- **natural_is_unspecified** (rdkit, openbabel, cdk, biotransformer, pyref, xenosmarts): isotope must equal the atom's label; unlabeled atoms match no isotope

Minimal example: `[12C]` on `C` [match]: `isotope_ignored` → `match:1`, `natural_is_unspecified` → `match:0`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar); refined by flipcheck 2026-10-03 ([13C] matches unlabeled C too)

### `products.byproduct_filter`

Small byproducts (H2O, NH3, HCl, formaldehyde) kept or dropped

- **blocklist** (biotransformer): BioTransformer isUnneccessaryMetabolite drops H2O/NH3/HCl/HCHO/CO2...; methanol kept
- **kept** (rdkit, chematic, cdk, pyref, xenosmarts): every fragment returned
- **rejected** (openbabel): transform rejected

Minimal example: `[C:1][O:2]>>[C:1].[O:2]` on `CCO` [apply]: `blocklist` → `products:CC`, `kept` → `re:products:(.*\.)?(O|\[OH\]|\[O\])(\..*)?`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `products.fragment_objects`

Cleavage products: one object per fragment, or one disconnected object

- **per_template_component** (rdkit, chematic): one object per product-template component (RDKit, chematic)
- **rejected** (openbabel): transform rejected
- **single_object** (cdk, pyref, xenosmarts): one disconnected object per outcome (Ambit raw, pyref)
- **split_flattened** (biotransformer): fragments split, all sites merged into one de-duplicated set (BioTransformer B1)

Minimal example: `[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])O.[O:3][C:4]` on `CC(=O)OCC` [apply] (view=objects): `per_template_component` → `objects:CC(=O)O + CCO`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `products.grouped_product_component`

Product-side component grouping `([C:1].[O:2])`

- **ignored_split** (biotransformer): grouping ignored (BioTransformer split)
- **one_object** (rdkit, cdk, pyref): grouped components form one product object (RDKit)
- **rejected** (chematic, openbabel, xenosmarts): parse error

Minimal example: `[C:1][O:2]>>([C:1].[O:2])` on `CCO` [apply] (view=objects): `ignored_split` → `re:objects:[^.]*`, `one_object` → `re:objects:[^+|]*\.[^+|]*`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `products.new_double_bond_h`

H on atoms that gain a double bond in a cleavage (aldehyde / CO2 byproduct)

- **dummies** (cdk, pyref, xenosmarts): Ambit dummy atoms
- **h_adjusted** (rdkit, chematic): CC=O / O=C=O
- **h_kept_overvalent** (biotransformer): explicit-H substrate keeps H: C[CH2]=O, O=C=[OH] (BioTransformer; rules must delete [H])
- **rejected** (openbabel): transform rejected

Minimal example: `[C:1][C:2](=[O:3])[O:4]>>[C:1].[O:3]=[C:2]=[O:4]` on `CCCC(=O)O` [apply]: `dummies` → `re:products:.*\*.*`, `h_adjusted` → `products:CCC.O=C=O`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `products.spectator_components`

Components of a multi-component substrate that the template does not touch

- **dropped** (rdkit, chematic): only the reacted component is returned (RDKit, chematic)
- **kept** (openbabel, pyref, xenosmarts): the whole input comes back as one object, spectators included (Open Babel in-place, xenosmarts)
- **kept_labels** (cdk): kept, with Ambit implicit-H labels (cdk raw)
- **kept_split** (biotransformer): spectators kept as separate fragments; small ones may then hit the byproduct blocklist (BioTransformer)

Minimal example: `[N:1]>>[N+:1]` on `CN.CCCC` [apply] (view=objects): `dropped` → `objects:C[NH3+]`, `kept` → `objects:CCCC.C[NH3+]`

Discovered: sweep rdkit vs xenosmarts 2026-10-03

### `products.validity_filter`

BioTransformer isValidMetabolte (B5a) on products

- **bt_invalid_dropped** (biotransformer): peroxide, ketene and carbon-free fragments (H2S, HBr) dropped; gem-diol CC(O)O kept
- **kept** (rdkit, chematic, openbabel, cdk, pyref, xenosmarts): every product returned

Minimal example: `[O:1][H]>>[O:1]O` on `CCO` [apply] (explicit H): `bt_invalid_dropped` → `products:`, `kept` → `['re:products:.*O(\\]\\[)?O.*', 'error']`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.add_atom_with_explicit_h`

Add unmapped atom on reactant with explicit H

- **empty** (chematic): nothing (chematic)
- **h_aware** (rdkit): CCCl
- **h_not_adjusted** (biotransformer, pyref, xenosmarts): C[CH3]Cl (H not removed)
- **rejected** (openbabel): Open Babel Init fails
- **untyped** (cdk): Ambit dummies

Minimal example: `[C:1]>>[C:1]Cl` on `CC` [apply] (explicit H): `empty` → `products:`, `h_aware` → `products:CCCl`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.add_unmapped_atom`

Add unmapped product atom `[O:1]>>[O:1]C`

- **added** (rdkit, chematic, pyref, xenosmarts): CCOC
- **h_kept_overvalent** (biotransformer): explicit-H substrate, H never adjusted after the edit (BioTransformer pipeline)
- **rejected** (openbabel): Open Babel Init fails
- **untyped** (cdk): added but Ambit dummy labels

Minimal example: `[O:1]>>[O:1]C` on `CCO` [apply]: `added` → `products:CCOC`, `h_kept_overvalent` → `products:CC[OH]C`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.aromatic_output_form`

How an untouched aromatic ring is written in products

- **aromatic** (rdkit, chematic): aromatic SMILES kept (RDKit, chematic)
- **kekule** (biotransformer, xenosmarts): Kekule SMILES (BioTransformer, xenosmarts)
- **kekule_labels** (cdk): Kekule with Ambit implicit-H labels
- **rejected** (openbabel, pyref): identity template rejected (Open Babel)

Minimal example: `[CH3:1]>>[C:1]` on `Cc1ccccc1` [apply]: `aromatic` → `products:Cc1ccccc1`, `kekule` → `products:CC1=CC=CC=C1`

Discovered: sweep rdkit vs xenosmarts 2026-10-03

### `smirks.aromatic_product`

Products of edits on aromatic atoms

- **aromatic_preserved** (rdkit, chematic): phenol / benzene stay aromatic
- **dearomatized** (pyref): aromatic flags dropped and H refilled as saturated (pyref)
- **kekule_h_kept** (biotransformer): Kekule output, substituted ring C keeps its H (BioTransformer)
- **kekule_labels** (cdk): Kekule, H lost (Ambit implicit-H)
- **kekule_output** (xenosmarts): Kekule output, H correct (xenosmarts)
- **rejected** (openbabel): template rejected (Open Babel Init)

Minimal example: `[c:1]:[c:2]>>[c:1]:[c:2]` on `c1ccccc1` [apply]: `aromatic_preserved` → `products:c1ccccc1`, `dearomatized` → `products:C1CCCCC1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.bond_order_decrease_retyping`

Atoms whose bond order drops (C=O -> C-O): retyped or dummies

- **dummies** (pyref, xenosmarts): atoms become dummies (pyref, xenosmarts raw apply; differs from Ambit raw)
- **labels** (cdk): Ambit raw: H not filled, no dummies ([C][C][O])
- **retyped** (rdkit, chematic, openbabel, biotransformer): valid product (CCO; RDKit, chematic, Open Babel, BioTransformer final)

Minimal example: `[C:1]=[O:2]>>[C:1]-[O:2]` on `CC=O` [apply]: `dummies` → `re:products:.*\*.*`, `labels` → `products:[C][C][O]`

Discovered: fuzz rdkit vs pyref 2026-10-03

### `smirks.charge_hcount`

H count after setting a +-1 charge on a neutral atom

- **all_sites_in_place** (openbabel): every match transformed in one molecule (Open Babel)
- **cation_adds_h** (chematic): carbocation gains H (C[CH4+], chematic)
- **h_count_kept** (biotransformer): H count unchanged (C[CH3+], CC[OH-]; BioTransformer explicit H)
- **untyped** (cdk): Ambit dummies
- **valence_rule** (rdkit, pyref, xenosmarts): H from default valence of the charged atom ([CH2+]C, CC[OH2+], C[NH-])

Minimal example: `[C:1]>>[C+:1]` on `CC` [apply]: `all_sites_in_place` → `products:[CH2+][CH2+]`, `cation_adds_h` → `products:C[CH4+]`

Discovered: fuzz rdkit vs chematic 2026-10-03 (findings/rdkit__chematic/01361e5f50.json)

### `smirks.charge_plus2_hcount`

Set +2 on a neutral N: H count on product

- **h_added** (chematic): C[NH4+2] (chematic)
- **h_cleared** (pyref, xenosmarts): C[N+2] (H not refilled)
- **untyped** (cdk): Ambit: atom untyped ([*+2])
- **valence_reduced** (rdkit, openbabel, biotransformer): C[NH2+2]

Minimal example: `[N:1]>>[N+2:1]` on `CN` [apply]: `h_added` → `products:C[NH4+2]`, `h_cleared` → `products:C[N+2]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.colon_product_bond`

Product `:` between mapped atoms of a non-aromatic bond (A14)

- **aromatic_bond_written** (chematic): aromatic bond, atoms not aromatic (C:C, chematic)
- **aromatic_flag_set** (rdkit): bond and atoms flagged aromatic (cc, RDKit)
- **labels** (openbabel, cdk): no change; Ambit labels
- **no_change** (biotransformer, pyref, xenosmarts): `:` never changes a bond (Ambit A14)

Minimal example: `[#6:1]-[#6:2]>>[#6:1]:[#6:2]` on `CC` [apply]: `aromatic_bond_written` → `products:C:C`, `aromatic_flag_set` → `products:cc`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.delete_mapped_by_omission`

Mapped reactant atom omitted from products `[C:1]-[O:2]>>[C:1]`

- **deleted** (rdkit, chematic): atom deleted, H refilled
- **deleted_no_refill** (openbabel): deleted, radical left ([CH2]C, Open Babel)
- **rejected** (cdk, biotransformer, pyref, xenosmarts): map index not valid (Ambit A3)

Minimal example: `[C:1]-[O:2]>>[C:1]` on `CCO` [apply]: `deleted` → `products:CC`, `deleted_no_refill` → `products:[CH2]C`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.disconnect`

Product `.` splits components `[C:1][C:2]>>[C:1].[C:2]`

- **labels** (cdk): [C].[C] (Ambit implicit-H)
- **rejected** (openbabel): Open Babel Init fails
- **split** (rdkit, chematic, pyref, xenosmarts): C.C
- **split_deduped** (biotransformer): identical fragments merged: one C (BioTransformer)

Minimal example: `[C:1][C:2]>>[C:1].[C:2]` on `CC` [apply]: `labels` → `products:[C].[C]`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.edits_with_explicit_h`

Bond-order / add-atom edits when the reactant has explicit H

- **empty** (chematic): edits produce nothing with AddHs (chematic)
- **h_aware** (rdkit): H removed/refilled correctly (RDKit)
- **h_kept_overvalent** (biotransformer): explicit-H substrate, H never adjusted after the edit (BioTransformer pipeline)
- **h_not_adjusted** (openbabel): explicit H kept, valence exceeded (Open Babel)
- **untyped** (cdk, pyref, xenosmarts): Ambit dummies

Minimal example: `[C:1]-[C:2]>>[C:1]=[C:2]` on `CC` [apply] (explicit H): `empty` → `products:`, `h_aware` → `products:C=C`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.element_change`

Mapped atom changes element `[C:1]>>[N:1]`

- **applied** (rdkit): element rewritten (RDKit)
- **corrupt** (openbabel): applied with wrong H ([NH3][NH3], Open Babel)
- **ignored** (chematic): no-op, element kept (chematic)
- **rejected** (cdk, biotransformer, pyref, xenosmarts): rule rejected: map atom types inconsistent (Ambit A4)

Minimal example: `[C:1]>>[N:1]` on `CC` [apply] (explicit H): `applied` → `products:CN`, `corrupt` → `products:[NH3][NH3]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.equivalent_h_mappings`

Mappings that differ only by which explicit H on the same atom (A11)

- **collapsed** (biotransformer, xenosmarts): equivalent-H mappings collapse to one (Ambit FlagFilterEquivalentMappings, BioTransformer)
- **per_h_atom** (rdkit, chematic, cdk, pyref): one outcome per H atom
- **single_application** (openbabel): one in-place application (Open Babel)

Minimal example: `[H][#6:1][#8:2][H]>>[#6:1]=[#8:2]` on `CCO` [apply] (explicit H, view=count): `collapsed` → `outcomes:1`, `per_h_atom` → `outcomes:2`

Processing: The cdk adapter runs SMIRKSManager without FlagFilterEquivalentMappings (per_h_atom); BioTransformer sets it (collapsed).

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.explicit_h_apply`

Any edit on a reactant with explicit H (AddHs)

- **edits_empty** (chematic): most edits return nothing with AddHs (chematic)
- **h_aware** (rdkit): edits apply, H adjusted (RDKit)
- **h_kept** (openbabel, biotransformer, pyref, xenosmarts): edits apply, H count kept (CC[OH-]; Open Babel, BioTransformer, pyref)
- **untyped** (cdk): Ambit dummies

Minimal example: `[O:1]>>[O-:1]` on `CCO` [apply] (explicit H): `edits_empty` → `products:`, `h_aware` → `products:CC[O-]`

Discovered: fuzz rdkit vs chematic baseline 2026-10-03

### `smirks.fragmented_reactant`

Single reactant template with `.` components `[C:1].[O:2]>>[C:1][O:2]`

- **intermolecular_pair** (rdkit): each component matched on its own copy of the reactant (COCO, RDKit)
- **rejected** (chematic, openbabel, cdk, biotransformer, pyref, xenosmarts): error (Ambit NPE A8b, chematic, OB)

Minimal example: `[C:1].[O:2]>>[C:1][O:2]` on `CO` [apply]: `intermolecular_pair` → `products:COCO`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.h_atom_in_template`

Graph `[H]` in a SMIRKS reactant

- **explicit_only** (rdkit, chematic, pyref, xenosmarts): matches only with AddHs; H refilled
- **explicit_only_no_refill** (cdk): with AddHs, deleting H leaves [CH3] (Ambit)
- **implicit_matchable** (openbabel, biotransformer): matches implicit H (Open Babel)

Minimal example: `[C:1][H]>>[C:1]` on `C` [apply] (explicit H): `explicit_only` → `products:C`, `explicit_only_no_refill` → `products:[CH3]`

Processing: explicit_h toggles AddHs on the reactant before apply.

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.hcount_query_explicit_h`

`[CH3:1]>>[CH3:1]` on ethane with AddHs

- **empty** (chematic): no products (chematic)
- **pin_adds_h** (rdkit): C[CH6] (template H added to explicit H, RDKit)
- **preserved** (cdk, biotransformer, pyref, xenosmarts): CC
- **rejected** (openbabel): template rejected (Open Babel Init)

Minimal example: `[CH3:1]>>[CH3:1]` on `CC` [apply] (explicit H): `empty` → `products:`, `pin_adds_h` → `products:C[CH6]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.identity_labels`

Identity apply product labels with implicit vs explicit H

- **labels_need_explicit_h** (cdk): without AddHs products lose implicit H ([C][C]; Ambit)
- **organic** (rdkit, chematic, biotransformer, pyref, xenosmarts): products written as organic SMILES either way
- **rejected** (openbabel): identity transform rejected (Open Babel Init fails when left==right)

Minimal example: `[C:1]>>[C:1]` on `CC` [apply]: `labels_need_explicit_h` → `products:[C][C]`, `organic` → `products:CC`

Processing: CDK: run with explicit_h=True for readable products (convertImplicitToExplicitHydrogens before apply).

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.mapped_aromatic_nh`

H on an aromatic N-H when that atom is mapped in the SMIRKS

- **dearomatized** (pyref): ring saturated (pyref)
- **h_lost_when_mapped** (chematic): mapped [nH] loses its H: identity on pyrrole gives c1ccnc1 (chematic 1.0.30); unmapped ring N-H is fine
- **kekule** (biotransformer, xenosmarts): kept, output Kekule (BioTransformer, xenosmarts)
- **labels** (cdk): Ambit implicit-H labels
- **preserved** (rdkit): pyrrole N-H kept (RDKit)
- **rejected** (openbabel): identity template rejected (Open Babel)

Minimal example: `[n:1]>>[n:1]` on `c1cc[nH]c1` [apply]: `dearomatized` → `products:C1CCNC1`, `h_lost_when_mapped` → `products:c1ccnc1`

Discovered: flipcheck rdkit vs chematic 2026-10-03 (fuzzer, flips of h_atom_query / reactant_aromaticity)

### `smirks.multi_site_application`

Template that matches several sites of one molecule

- **all_sites_in_place** (openbabel): every site transformed in one product (Open Babel)
- **flattened_h_kept** (biotransformer): sites merged into one fragment set, explicit H kept (BioTransformer)
- **per_site** (rdkit, chematic, cdk, pyref, xenosmarts): one outcome per site (RDKit, chematic, Ambit, pyref)

Minimal example: `[O:1]>>[O-:1]` on `OCCO` [apply]: `all_sites_in_place` → `products:[O-]CC[O-]`, `flattened_h_kept` → `products:OCC[OH-]`

Discovered: fuzz rdkit vs openbabel 2026-10-03

### `smirks.nested_recursive`

Nested recursive SMARTS in SMIRKS reactant (apply path)

- **always_true** (cdk, biotransformer, xenosmarts): nested $() true: identity applies (Ambit A7b)
- **evaluated** (rdkit, pyref): nested $() evaluated: no products on ethane
- **rejected** (chematic, openbabel): parse error

Minimal example: `[C;$(C[$(O)]):1]>>[C:1]` on `CC` [apply]: `always_true` → `re:products:.+`, `evaluated` → `products:`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.neutralize_written_charge`

Reactant `[N+:1]` -> product `[N:1]`

- **inherited** (rdkit): product charge unwritten -> reactant charge kept (RDKit)
- **neutralized** (chematic, openbabel, pyref, xenosmarts): charge set to 0
- **neutralized_h_kept** (biotransformer): charge 0, H count kept: C[NH3] (BioTransformer)
- **untyped** (cdk): Ambit untyped

Minimal example: `[N+:1]>>[N:1]` on `C[NH3+]` [apply]: `inherited` → `products:C[NH3+]`, `neutralized` → `products:CN`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.new_bond_query_order`

New product bond with query order `~` (A6)

- **bond_dropped** (pyref, xenosmarts): atom added, bond skipped (C.CC; pyref, xenosmarts)
- **query_bond_copied** (rdkit, chematic): product keeps a query bond (CC~C; RDKit, chematic)
- **rejected** (openbabel, cdk, biotransformer): undefined order error (Ambit A6, Open Babel)

Minimal example: `[C:1]>>[C:1]~C` on `CC` [apply]: `bond_dropped` → `re:products:.*C\.CC.*`, `query_bond_copied` → `products:CC~C`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.outcome_multiplicity`

How many outcomes per match set

- **all_mappings** (rdkit): one outcome per ordered mapping (RDKit RunReactants)
- **deduped_products** (chematic): unique atom sets, identical products merged (chematic)
- **flattened** (biotransformer): all sites merged into one fragment set (BioTransformer)
- **single_application** (openbabel): one in-place application (Open Babel)
- **unique_atom_sets** (cdk, pyref, xenosmarts): one per atom set (Ambit non-identical A8)

Minimal example: `[C:1]-[C:2]>>[C:1]=[C:2]` on `CC` [apply] (view=count): `all_mappings` → `outcomes:2`, `deduped_products` → `outcomes:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.product_h_atom_added`

Product adds a graph `[H]` `[O:1]>>[O:1][H]` on an anion

- **h_added_charge_kept** (biotransformer, pyref, xenosmarts): CC[OH-]
- **h_dropped** (rdkit): H atom dropped, charge kept (CC[O-])
- **protonated_reset** (chematic): H added and charge reset (CCO, chematic)
- **rejected** (openbabel): template rejected (Open Babel Init)
- **untyped** (cdk): Ambit dummies

Minimal example: `[O:1]>>[O:1][H]` on `CC[O-]` [apply]: `h_added_charge_kept` → `products:CC[OH-]`, `h_dropped` → `products:CC[O-]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.product_h_pin`

Product H count `[C:1]>>[CH2:1]`

- **authoritative** (rdkit): product H sets the count ([CH2]C); with AddHs H atoms add on top (C[CH5])
- **ignored** (biotransformer, pyref, xenosmarts): product H ignored
- **labels** (cdk): ignored; Ambit labels
- **rejected** (openbabel): template rejected (Open Babel Init)
- **rejected_empty** (chematic): no outcomes (chematic)

Minimal example: `[C:1]>>[CH2:1]` on `CC` [apply]: `authoritative` → `products:[CH2]C`, `ignored` → `products:CC`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.product_only_map`

Map number only on the product side `[C:1]>>[C:1][N:2]`

- **created** (rdkit, chematic): atom created as if unmapped
- **rejected** (openbabel, cdk, biotransformer, pyref, xenosmarts): map index not valid

Minimal example: `[C:1]>>[C:1][N:2]` on `CC` [apply]: `created` → `products:CCN`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.product_plusplus`

`++` on product side equals `+2`

- **same_as_plus2** (rdkit, chematic, openbabel, biotransformer, pyref, xenosmarts): C[NH2+2] / C[NH4+2] like +2
- **untyped** (cdk): Ambit untyped

Minimal example: `[N:1]>>[N++:1]` on `CN` [apply]: `same_as_plus2` → `['products:C[NH2+2]', 'products:C[NH4+2]', 'products:C[N+2]']`, `untyped` → `re:products:.*\*.*`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.reactant_aromaticity`

Aromaticity the SMIRKS reactant matcher sees on Kekule / exocyclic-C=O rings

- **cdk_model** (biotransformer): benzene aromatic, 4-pyranone not (BioTransformer B0: ElectronDonation.cdk)
- **daylight_perceived** (rdkit, pyref, xenosmarts): Kekule benzene and 4-pyranone aromatic (RDKit, pyref)
- **not_perceived** (chematic, cdk): input aromaticity taken as written: Kekule benzene matches [C:1], aromatic-spelled pyranone does not (chematic run_smirks, raw Ambit)
- **rejected** (openbabel): transform rejected

Minimal example: `[C:1]>>[C:1]` on `O=C1C=COC=C1` [apply]: `cdk_model` → `re:products:.+`, `daylight_perceived` → `products:`

Discovered: fuzz rdkit vs chematic baseline 2026-10-03

### `smirks.reactant_query_syntax`

SMARTS logic (`;` `,` `!`, D/X) on SMIRKS reactant atoms

- **full_smarts** (rdkit, cdk, biotransformer, pyref, xenosmarts): reactant side is SMARTS
- **smiles_only** (chematic, openbabel): reactant side parsed as SMILES: `;`, `,`, `!`, X, D fail (chematic run_smirks)

Minimal example: `[N;#7:1]>>[N:1]` on `CC#N` [apply]: `full_smarts` → `re:products:.+`, `smiles_only` → `error`

Discovered: fuzz rdkit vs chematic (molecule-first generator) 2026-10-03

### `smirks.recursive_in_reactant`

Recursive SMARTS on a mapped reactant atom

- **rejected** (chematic, openbabel): SMIRKS parse error (chematic Q07, Open Babel)
- **supported** (rdkit, cdk, biotransformer, pyref, xenosmarts): matches and applies

Minimal example: `[C;$(CO):1]>>[C:1]` on `CCO` [apply]: `rejected` → `error`, `supported` → `['products:CCO', 'products:[C][C][O]']`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.sanitize_policy`

Lib-native sanitize on valence-invalid products

- **drops_invalid** (rdkit): ether and neutral iminium dropped (RDKit SanitizeMol)
- **h_kept_overvalent** (biotransformer): explicit-H substrate, H never adjusted after the edit (BioTransformer pipeline)
- **keeps_all** (openbabel): nothing dropped (Open Babel)
- **keeps_hypervalent_n** (chematic): ether dropped, neutral 4-valent N kept (chematic)
- **untyped** (cdk): Ambit dummies survive

Minimal example: `[C:1][O:2]>>[C:1]=[O:2]` on `COC` [apply] (view=sanitized): `drops_invalid` → `products:`, `h_kept_overvalent` → `products:CO=[CH3]`

Processing: Layer S: each engine's own sanitizer only (smirks_apply.sanitize_product).

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.site_choice_order_dependence`

Which mapping/site survives depends on input atom order

- **mapping_order_dependent** (chematic, openbabel): symmetric pattern: which end is which follows atom order (chematic, Open Babel)
- **order_independent** (rdkit, cdk, pyref, xenosmarts): same products for every spelling of the molecule
- **site_order_dependent** (biotransformer): several sites: which site survives follows atom order (BioTransformer, Ambit A8c)

Minimal example: `[C:1][C:2]>>[C:1]` on `CCO` [apply]: `mapping_order_dependent` → `re:.* / .*`, `order_independent` → `re:[^/]*`

Discovered: autoconf stability check 2026-10-03 (systematic reorderings)

### `smirks.star_on_explicit_h`

Mapped `*` on a substrate with explicit H atoms

- **always_explicit** (biotransformer): substrate is always explicit-H: `*` edits H atoms even in a plain run (BioTransformer)
- **explicit_edits_empty** (chematic): nothing with AddHs (chematic)
- **h_atoms_no_refill** (pyref, xenosmarts): H atoms reached with AddHs, H count not refilled (pyref)
- **h_atoms_when_explicit** (rdkit): `*` reaches H atoms only after AddHs; H substituted (RDKit)
- **rejected** (openbabel): transform rejected
- **untyped** (cdk): Ambit dummies

Minimal example: `[*:1]>>[*:1]Cl` on `C` [apply] (explicit H): `always_explicit` → `products:C[H]Cl`, `explicit_edits_empty` → `products:`

Discovered: fuzz cdk vs biotransformer 2026-10-03

### `smirks.star_retype`

Typed reactant map rewritten as product `*` `[O:1]>>[*:1]C(=O)C`

- **corrupt** (openbabel): [*H]CC (Open Babel)
- **keeps_reactant_atom** (rdkit, chematic): acetyl ester
- **rejected** (cdk, biotransformer, pyref, xenosmarts): map atom types inconsistent (Ambit A4)

Minimal example: `[O:1]>>[*:1]C(=O)C` on `CCO` [apply]: `corrupt` → `products:[*H]CC`, `keeps_reactant_atom` → `products:CCOC(C)=O`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.stereo_carried`

Tetrahedral stereo on an atom carried through an edit next to it

- **dropped** (biotransformer, pyref, xenosmarts): stereo removed (BioTransformer, pyref)
- **flipped_by_neighbor_order** (chematic): parity inverted when the mapped atom is a particular neighbor (chematic 1.0.30 bug)
- **labels** (cdk): Ambit labels, stereo dropped
- **preserved** (rdkit): parity kept (RDKit)
- **rejected** (openbabel): transform rejected (Open Babel identity)

Minimal example: `[CH3:1]>>[C:1]` on `C[C@H](N)O` [apply]: `dropped` → `products:CC(N)O`, `flipped_by_neighbor_order` → `products:C[C@@H](N)O`

Discovered: fuzz rdkit vs chematic baseline 2026-10-03

### `smirks.undefined_order_both_sides`

Query order on both sides between mapped atoms `-,:` >> `=,:` (A6b)

- **first_alternative** (rdkit): first product alternative applied (C=C, RDKit)
- **noop_applied** (cdk, biotransformer, pyref, xenosmarts): reported, bond edit skipped, rest applied (Ambit A6b)
- **rejected** (chematic, openbabel): rule rejected

Minimal example: `[#6:1]-,:[#6:2]>>[#6:1]=,:[#6:2]` on `CC` [apply]: `first_alternative` → `products:C=C`, `noop_applied` → `['products:CC', 'products:[C][C]']`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.undefined_product_bond`

Product bond with query order `=,:` on mapped atoms

- **first_alternative** (rdkit): first alternative applied (C=C)
- **rejected** (chematic, cdk, biotransformer): rule rejected
- **skipped** (openbabel, pyref, xenosmarts): bond edit skipped, rest applied (Ambit A6b / OB)

Minimal example: `[C:1]-[C:2]>>[C:1]=,:[C:2]` on `CC` [apply]: `first_alternative` → `products:C=C`, `rejected` → `error`

Processing: CDK adapter raises on SMIRKSManager errors; BioTransformer ignores A6b errors and applies (adapter policy).

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.unmapped_reactant_deleted`

Unmapped reactant atom `[C:1]O>>[C:1]`

- **deleted** (rdkit, chematic, biotransformer): deleted, H refilled (also with AddHs)
- **deleted_h_orphaned** (pyref, xenosmarts): with AddHs the O's H atom is left as a fragment (pyref)
- **labels_h_orphaned** (cdk): implicit-H run gives [C][C]; AddHs run orphans the H (Ambit)
- **rejected** (openbabel): rule rejected

Minimal example: `[C:1]O>>[C:1]` on `CCO` [apply] (explicit H): `deleted` → `products:CC`, `deleted_h_orphaned` → `re:products:.*\[H.*`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.unwritten_charge`

`[N:1]>>[N:1]` on a charged reactant atom

- **inherited** (rdkit, biotransformer, pyref, xenosmarts): charge kept
- **labels** (cdk): charge kept, H lost ([C][N+], Ambit implicit-H)
- **rejected** (openbabel): identity rejected
- **reset** (chematic): charge cleared to 0 (chematic)

Minimal example: `[N:1]>>[N:1]` on `C[NH3+]` [apply]: `inherited` → `products:C[NH3+]`, `labels` → `products:[C][N+]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `smirks.valence_invalid_raw`

Raw edit product that breaks valence (ether -> C=O)

- **dropped_at_apply** (chematic): valence check drops it (chematic)
- **h_kept_overvalent** (biotransformer): explicit-H substrate, H never adjusted after the edit (BioTransformer pipeline)
- **hypervalent** (openbabel): C=O=C (Open Babel)
- **kept_raw** (rdkit): unsanitized C=OC kept (RDKit Layer E)
- **untyped** (cdk, pyref, xenosmarts): Ambit dummies

Minimal example: `[C:1][O:2]>>[C:1]=[O:2]` on `COC` [apply]: `dropped_at_apply` → `products:`, `h_kept_overvalent` → `products:CO=[CH3]`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.aliphatic_any_A`

`A` aliphatic any atom

- **rejected** (pyref): parse error
- **supported** (rdkit, chematic, openbabel, cdk, biotransformer, xenosmarts): parses and matches (core OpenSMARTS)

Minimal example: `[A]` on `c1ccccc1C` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.aliphatic_hetero_neighbors_Z`

RDKit `Z` aliphatic heteroatom-neighbor count

- **rejected** (chematic, openbabel, cdk, biotransformer): parse error
- **supported** (rdkit, pyref, xenosmarts): parses and matches (RDKit-only extension)

Minimal example: `[CZ1]` on `CO` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.aromatic_selenium`

aromatic `se` in brackets

- **rejected** (pyref, xenosmarts): parse error
- **supported** (rdkit, chematic, openbabel, cdk, biotransformer): parses and matches (core OpenSMARTS)

Minimal example: `[se]` on `c1cc[se]c1` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.cdk_hash_X`

CDK `#X` any non-C non-H

- **rejected** (rdkit, chematic, openbabel): parse error
- **supported** (cdk, biotransformer, pyref, xenosmarts): parses and matches (CDK-only extension)

Minimal example: `[#X]` on `CO` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.component_grouping`

Component-level grouping `(C).(O)` / `(C.O)`

- **enforced** (cdk, biotransformer): groups constrain components
- **ignored** (openbabel, pyref): parentheses accepted, grouping ignored
- **rejected** (rdkit, chematic, xenosmarts): parse error

Minimal example: `(C).(O)` on `CO` [match]: `enforced` → `match:0`, `ignored` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.dative_bond`

RDKit dative bonds `->` / `<-` in SMARTS

- **rejected** (chematic, openbabel, cdk, biotransformer, xenosmarts): parse error
- **supported** (rdkit, pyref): parses

Minimal example: `N->[Fe]` [parse]: `rejected` → `error`, `supported` → `ok`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.dot_disconnected`

Disconnected `.` query without grouping

- **rejected** (openbabel): parse error (Open Babel)
- **supported** (rdkit, chematic, cdk, biotransformer, pyref, xenosmarts): C.O matches methanol (no component constraint)

Minimal example: `C.O` on `CO` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.hetero_neighbors_z`

RDKit `z` heteroatom-neighbor count

- **rejected** (chematic, openbabel, cdk, biotransformer): parse error
- **supported** (rdkit, pyref, xenosmarts): parses and matches (RDKit-only extension)

Minimal example: `[Cz1]` on `CO` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.hybridization`

`^n` hybridization digits: which digits parse and what they match

- **cdk_one_based_untyped** (cdk, biotransformer): CDK SmartsPattern: ^0 rejected; ^3 does not match unless atoms are hybridization-typed
- **lenient_digits** (chematic): chematic 1.0.30: accepts ^0..^7, bare ^ rejected
- **openbabel_bare** (openbabel): Open Babel: bare ^ means ^1 (SP); ^0 accepted
- **unsupported** (pyref, xenosmarts): parses but matching raises (no perceived hybridization)
- **zero_to_five** (rdkit): RDKit: ^0..^5 (S..SP3D2); ^7 rejected; bare ^ rejected

Minimal example: `[C^0]` [parse]: `cdk_one_based_untyped` → `error`, `lenient_digits` → `ok`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.insaturation_i`

CDK/CACTVS `i<n>` insaturation

- **parsed_no_match** (chematic): parses, matches nothing (chematic)
- **rejected** (rdkit, openbabel): parse error
- **supported** (cdk, biotransformer, pyref, xenosmarts): i1 matches atoms with one pi bond

Minimal example: `[Ci1]` on `C=C` [match]: `parsed_no_match` → `match:0`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.periodic_group_G`

CDK `G<n>` periodic group

- **rejected** (rdkit, chematic, openbabel, cdk, biotransformer): parse error
- **supported** (pyref, xenosmarts): parses and matches (CDK-documented; jar SmartsPattern rejects)

Minimal example: `[G16]` on `CO` [match]: `rejected` → `error`, `supported` → `match:1`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.range_counts`

RDKit `{lo-hi}` count ranges

- **rejected** (chematic, openbabel): parse error
- **supported** (rdkit, cdk, biotransformer, pyref, xenosmarts): parses and matches (RDKit-only extension)

Minimal example: `[CD{1-2}]` on `CCC` [match]: `rejected` → `error`, `supported` → `match:3`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.ring_size_k`

`k<n>` member of any ring of size n

- **rejected** (openbabel, cdk, biotransformer): parse error
- **supported** (rdkit, chematic, pyref, xenosmarts): parses and matches (RDKit/chematic extension)

Minimal example: `[Ck6]` on `C1CCC2CCCC2C1` [match]: `rejected` → `error`, `supported` → `match:6`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

### `syntax.unclosed_ring`

Unclosed ring-closure digit in SMARTS

- **accepted** (pyref, xenosmarts): accepted (smarts_grammar records QueryMol.open_rings)
- **rejected** (rdkit, chematic, openbabel, cdk, biotransformer): parse error

Minimal example: `C1CC` [parse]: `accepted` → `ok`, `rejected` → `error`

Discovered: 2026-10-03 autoconf discovery matrix (rdkit 2026.03.6, chematic 1.0.30, openbabel 3.2.1, cdk 2.7.1+ambit bt-jar)

