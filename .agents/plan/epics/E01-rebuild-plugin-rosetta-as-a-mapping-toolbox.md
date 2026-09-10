# E01 Epic: rebuild plugin rosetta as a mapping toolbox

## Goal

Deliver `plugin-rosetta` as an installable, mapping-agnostic Python toolbox that migrates the working behaviour of [`sssom-rosetta`](https://github.com/plugin-healthcare/sssom-rosetta) into a clean package and publishes open-standard mapping, ontology, and vocabulary artifacts.

## Background

`sssom-rosetta` works but mixes healthcare-specific pipelines, hardcoded source registries, CLI logic, and build wiring in one place.

`plugin-rosetta` currently contains only scaffolding: `src/plugin-rosetta/__init__.py` is not a valid import package, so `uv run` fails with `Expected a Python module at: src/plugin_rosetta/__init__.py`.

The authored mapping content and mapping-set configuration are already preserved under `registry/`, so the rebuild can start from tracked content instead of re-deriving it.

The plan of record is [`.agents/plan/20260901_migration_plan.md`](../20260901_migration_plan.md); this epic follows its milestone sequence and its deferred list.

## Scope

### In scope

- An installable `plugin-rosetta` distribution with the `plugin_rosetta` import package, the `uv_build` backend, and a thin `rosetta` CLI.
- Tracked mapping-set configuration, CSVW mapping reading, and SSSOM, Turtle, Markdown, and HTML outputs.
- Tracked ontology source configuration, reproducible download and cache reuse, and referential validation of mappings.
- Vocabulary release ingest and the OMOP, DHD, LOINC-SNOMED, and SNOMED International graph pipelines plus graph merge.
- A basic local artifact catalogue with content-addressed versions, provenance manifests, and differences.
- A migration parity check, a capability matrix, a README quickstart, and a runnable example.

### Out of scope

- FHIR-to-OMOP and OMOP-to-FHIR transformation artifacts and any FHIR runtime.
- SQL on FHIR and Ariadne-based mapping generation or evaluation.
- A mapping UI and a separate reusable runtime package.
- S3-compatible or any remote artifact storage.
- Aliases, promotion, rollback, registry metadata migration, and garbage collection.
- Gephi and Protege exports (`src/sssom_rosetta/mapping/gephi.py` and `src/sssom_rosetta/mapping/protege.py` are not migrated).

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Installable package | `uv run` fails to build `src/plugin-rosetta` | a clean checkout installs and `rosetta --help` exits 0 |
| Quality gate | `tara check` cannot run | `tara check` passes on every story |
| Preserved mapping rows readable by the package | 0 of 8 rows in `registry/mappings/omop-onz-g.csv` | 8 of 8 rows read, validated, and published without value changes |
| Retained legacy modules migrated | 0 of 22 (24 `sssom-rosetta` modules minus `gephi.py` and `protege.py`) | 22 of 22 migrated or explicitly folded into a migrated module |
| Source definitions in tracked configuration | 0 (2 ontology and 4 vocabulary sources live in Python globals) | 2 in `registry/config/ontology-sources.yaml` and 4 in `registry/config/vocabulary-sources.yaml` |
| Retained legacy workflows with a named replacement test | 0 | every retained workflow has at least one replacement test |
| Published outputs proven readable without importing `plugin_rosetta` | 0 formats | SSSOM/TSV, Turtle, Markdown, JSON, and YAML outputs each covered by an independent-reader test |
| Explicitly covered failure conditions | 0 of 7 (missing checksum, unknown prefix, missing identifier, nondeterministic label, collapsed empty cell, null template omission, partial output) | 7 of 7 covered by a test |

## Stories

- [x] [E01-S01 Establish the installable package and shared contracts](../stories/E01-S01-establish-the-installable-package-and-shared-contracts.md)
- [x] [E01-S02 Preserve and validate mapping set configuration](../stories/E01-S02-preserve-and-validate-mapping-set-configuration.md)
- [x] [E01-S03 Read authored CSVW mapping sets](../stories/E01-S03-read-authored-csvw-mapping-sets.md)
- [x] [E01-S04 Write open mapping artifacts and reports](../stories/E01-S04-write-open-mapping-artifacts-and-reports.md)
- [x] [E01-S05 Configure and download ontology sources](../stories/E01-S05-configure-and-download-ontology-sources.md)
- [x] [E01-S06 Validate mappings against ontology catalogs](../stories/E01-S06-validate-mappings-against-ontology-catalogs.md)
- [ ] [E01-S07 Ingest versioned vocabulary releases](../stories/E01-S07-ingest-versioned-vocabulary-releases.md)
- [ ] [E01-S08 Build the OMOP vocabulary graph](../stories/E01-S08-build-the-omop-vocabulary-graph.md)
- [ ] [E01-S09 Build the DHD thesaurus graphs](../stories/E01-S09-build-the-dhd-thesaurus-graphs.md)
- [ ] [E01-S10 Build RF2 graphs and merge vocabularies](../stories/E01-S10-build-rf2-graphs-and-merge-vocabularies.md)
- [ ] [E01-S11 Compare local artifact versions](../stories/E01-S11-compare-local-artifact-versions.md)
- [ ] [E01-S12 Complete migration parity and release](../stories/E01-S12-complete-migration-parity-and-release.md)

## Dependencies

- Read access to the `sssom-rosetta` repository as the migration reference for source modules, tests, and fixtures.
- Maplib as a core dependency for large vocabulary graph construction and merge.
- RDFLib, csvw, curies, linkml-runtime, sssom-py, Polars, Pydantic, Typer, and an HTTP client as direct dependencies.
- `sssom-schema` pinned to `1.1.0a5`, the exact version that generated the legacy `src/sssom_rosetta/models/sssom.py`.
- Nyctea for tabular vocabulary release validation, introduced with the vocabulary ingest slice.
- A curator with a licence for the Athena OMOP bundle, the DHD thesauri portal, and the SNOMED International and LOINC-SNOMED RF2 packages, because those releases have no open download URL.
- `tara` for the `check` gate that every story must pass.

## Open Questions

- The `author_label` value `sssom-rosetta contributors` in `registry/mappings/omop-onz-g.csv` does not match any `author_label` in `registry/mappings/contributors.csv`; the mapping curator must either approve a reviewed correction or record a decision to retain the legacy value for compatibility.
- `mapping_set_id` in `registry/config/mapping-sets.yaml` still points at the `sssom-rosetta` build URL; the curator must decide the replacement identifier and how the previous identifier is recorded as provenance.
- Which Nyctea version to pin, and whether it is available as a published dependency at the time E01-S07 starts.
