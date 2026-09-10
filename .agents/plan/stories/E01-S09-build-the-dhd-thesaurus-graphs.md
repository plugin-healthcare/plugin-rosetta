# E01-S09 Story: build the DHD thesaurus graphs

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **vocabulary curator**,
I want **the DHD Diagnosethesaurus and Verrichtingenthesaurus releases turned into SKOS Turtle graphs with their SNOMED, ICD-10, and DBC links**,
so that **Dutch hospital thesaurus concepts are usable as RDF and connect to OMOP through shared identifiers**.

## Value

DHD is the second format slice and the one with genuinely different semantics: validity windows, multilingual labels, and specialty-scoped DBC identity.

Two working adapters make it possible to extract the shared source-adapter contract from evidence instead of guessing it.

## Prerequisites

- [E01-S08 Build the OMOP vocabulary graph](E01-S08-build-the-omop-vocabulary-graph.md) for the namespaces, templates, Maplib writer, and provenance sidecar.

## Scope

### In scope

- DHD `uitleverformaat4.3` CSV reading with quoted fields and text-only columns.
- As-of validity filtering per table using the release validity window.
- Concept, SNOMED FSN term, preferred label, ICD-10 derivation, and DBC derivation loading.
- Specialty-scoped DBC diagnosis identity and the DBC IRI scheme.
- The DHD concept and close-match OTTR templates and DT and VT graph construction.
- Format-version assertion and release-directory location for DT and VT.
- Thin `rosetta vocabulary build-dhd-diagnosethesaurus` and `build-dhd-verrichtingenthesaurus` commands.
- Extraction of the shared source-adapter contract proven by OMOP and DHD, with contract tests.

### Out of scope

- LOINC-SNOMED and SNOMED International RF2 builds and graph merge; those are E01-S10.
- Any DHD derivation beyond ICD-10 and DBC.
- Temporal history: only the as-of state is materialised.

## Acceptance Criteria

- [ ] GIVEN a synthetic DHD release, WHEN a concept table is read, THEN all columns are text, quoted fields are honoured, and identifiers keep any leading zeros.
- [ ] GIVEN rows with validity windows around the as-of date, WHEN a table is filtered, THEN only rows valid on that date are kept, and a row with a blank end date counts as still valid.
- [ ] GIVEN a concept with concurrently active English and Dutch fully specified names, WHEN the preferred label is loaded, THEN the Dutch label is chosen and tagged `nl`, deterministically across runs.
- [ ] GIVEN a concept with only an English fully specified name, WHEN the preferred label is loaded, THEN the English label is chosen and tagged `en`.
- [ ] GIVEN a concept with concurrently active English and Dutch fully specified name rows carrying the same SNOMED identifier, WHEN SNOMED terms are loaded, THEN exactly one row is returned for that concept.
- [ ] GIVEN an ICD-10 derivation table with blank and inactive rows, WHEN it is loaded, THEN blank codes and inactive rows are excluded and multiple candidates per concept are all kept.
- [ ] GIVEN two DBC derivation rows that share a `DBC_ID` under different `SpecialismeCode` values, WHEN they are loaded, THEN they produce two distinct composite identifiers of the form `<SpecialismeCode>-<DBC_ID>` and two distinct DBC IRIs.
- [ ] GIVEN a DBC derivation row with a blank `DBC_ID`, WHEN it is loaded, THEN the row is dropped.
- [ ] GIVEN a loaded DT release, WHEN the graph is built, THEN concepts are typed `skos:Concept`, carry their preferred label, carry `skos:exactMatch` to SNOMED where present, and carry `skos:closeMatch` to their ICD-10 and DBC codes.
- [ ] GIVEN a loaded VT release, WHEN the graph is built, THEN it contains SNOMED links only and no ICD-10 or DBC triples.
- [ ] GIVEN a DT and a VT concept with the same numeric identifier, WHEN both graphs are built, THEN they mint IRIs in different namespaces and do not collide.
- [ ] GIVEN a concept with no active SNOMED mapping or no label, WHEN the graph is built, THEN no triple is emitted for the absent value and the concept node still exists.
- [ ] GIVEN a release whose directory does not carry the configured format-version marker, WHEN a build is requested, THEN it fails naming the expected marker rather than mis-parsing columns.
- [ ] GIVEN a release in which zero or several directories match a thesaurus, WHEN the release directory is located, THEN the error lists what was found.
- [ ] GIVEN the OMOP and both DHD adapters, WHEN the shared adapter contract test suite runs, THEN each adapter builds from a release directory, writes Turtle, and writes a provenance sidecar through the same contract.
- [ ] GIVEN an ingested synthetic release, WHEN each DHD build command runs, THEN it exits 0, writes its Turtle output and sidecar, and the command body contains no graph logic.

## Technical Tasks

- [ ] Add `src/plugin_rosetta/vocabulary/dhd.py` with the release scan, the as-of filter, `load_concepts`, `load_snomed_terms`, `load_labels`, `load_icd10`, `load_dbc`, and `build_graph`.
- [ ] Make label selection explicitly deterministic by ordering on a declared language preference rather than relying on incidental sort order of language codes.
- [ ] Keep the DBC composite identity in `load_dbc` and add `dbc_iri` alongside the DHD concept IRI helpers in `src/plugin_rosetta/vocabulary/namespaces.py`.
- [ ] Add the DHD concept and close-match templates to `src/plugin_rosetta/vocabulary/templates.py`.
- [ ] Read the format version from the tracked vocabulary source configuration and assert it in `build_from_release`, with no duplicate constant in code.
- [ ] Validate each loaded DHD frame against its declared table contract from E01-S07 instead of the legacy in-module column set.
- [ ] Extract the shared adapter contract only after both DHD builds pass: a protocol or small registry describing build from release, write, and provenance, replacing per-source duplication in the application layer.
- [ ] Add contract tests that run the OMOP and both DHD adapters through the same assertions.
- [ ] Add the two thin DHD build commands and `justfile` recipes.
- [ ] Add `tests/vocabulary/test_dhd.py` and `tests/vocabulary/test_adapter_contract.py` driven by synthetic DT and VT fixtures.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/vocabulary/dhd.py` `_scan_dhd`, `_active`, `_non_blank` | `src/plugin_rosetta/vocabulary/dhd.py` | Column checks move to the declared contracts from E01-S07 |
| `src/sssom_rosetta/vocabulary/dhd.py` `load_concepts`, `load_snomed_terms`, `load_labels`, `load_icd10` | `src/plugin_rosetta/vocabulary/dhd.py` | Behaviour preserved, label choice made explicitly deterministic |
| `src/sssom_rosetta/vocabulary/dhd.py` `load_dbc` composite `SpecialismeCode`-`DBC_ID` identity | `src/plugin_rosetta/vocabulary/dhd.py` | Load bearing: a raw `DBC_ID` is not unique across specialisms |
| `src/sssom_rosetta/vocabulary/namespaces.py` `dbc_iri`, `dhd_concept_iri`, `THESAURUS_NAMESPACES`, `UnknownThesaurusError` | `src/plugin_rosetta/vocabulary/namespaces.py` | Keep DT and VT in separate namespaces |
| `src/sssom_rosetta/vocabulary/dhd.py` `_concept_rows`, `_close_match_rows`, `DhdCrossLinks`, `build_graph`, `write_ttl` | `src/plugin_rosetta/vocabulary/dhd.py` | Keep the optional-parameter drop semantics |
| `src/sssom_rosetta/vocabulary/dhd.py` `FORMAT_VERSION`, `_find_release_dir`, `_exact_suffix`, `DhdFormatVersionError` | `src/plugin_rosetta/vocabulary/dhd.py` plus `registry/config/vocabulary-sources.yaml` | The format version comes from tracked configuration |
| `src/sssom_rosetta/vocabulary/templates.py` `DHD_CONCEPT_TEMPLATE`, `DHD_CLOSE_MATCH_TEMPLATE` and their IRIs | `src/plugin_rosetta/vocabulary/templates.py` | Behaviour preserved |
| `src/sssom_rosetta/vocabulary/pipeline.py` `BuildTarget`, `BUILD_TARGETS`, `get_build_target`, `build_target`, `MissingReleaseError` | `src/plugin_rosetta/vocabulary/adapters.py` | Extracted here, after two adapters prove the contract |
| `src/sssom_rosetta/cli.py` `vocabulary build-dhd-diagnosethesaurus` (line 638), `build-dhd-verrichtingenthesaurus` (line 649), `_run_build_target` (line 594) | `src/plugin_rosetta/vocabulary/api.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to the public feature API |
| `sssom-rosetta/tests/vocabulary/test_dhd.py` | `tests/vocabulary/test_dhd.py` | Port the active-window, dedupe, blank-exclusion, specialty-disambiguation, namespace-separation, and Dutch-preference cases |

## Edge Cases

- The specialty-scoped DBC identity is easy to lose in a refactor and silently produces merged, wrong concepts, so it needs its own regression test.
- Dates are fixed-width `YYYYMMDD` strings, so string comparison is correct only while the width holds; a malformed date must fail rather than compare wrongly.
- A blank end date means still valid, while a blank start date is a data error and must be reported.
- DT and VT concept identifiers can collide as strings, which is exactly why the namespaces differ.
- The as-of date defaults to today, which makes a build non-reproducible; the effective as-of date must be recorded in the provenance sidecar and be overridable.
- The ingested DHD ZIP nests DT and VT under one release, so both builds read from the same ingested directory.
- Extracting the adapter contract before both DHD builds pass would encode OMOP-specific assumptions, so the extraction task is deliberately last.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/vocabulary` passes offline against synthetic fixtures.
- [ ] `uv run tara check` passes.
- [ ] The vocabulary documentation records the DHD IRI schemes, the DBC identity rule, the language preference, and the as-of behaviour.
- [ ] The Turtle outputs parse in a process that does not import `plugin_rosetta`.
- [ ] Acceptance criteria verified with the vocabulary curator on a real ingested DHD release, with only counts and output paths reported.
- [ ] No licensed release payload, extracted file, or generated graph is staged; every committed fixture is synthetic.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

The extracted adapter contract must cover only what OMOP and DHD both need.

RF2 sources join the same contract in E01-S10; if they do not fit, the contract is corrected there rather than widened speculatively now.
