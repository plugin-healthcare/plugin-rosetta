# E01-S08 Story: build the OMOP vocabulary graph

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **vocabulary curator**,
I want **an ingested OMOP Athena release turned into a SKOS Turtle graph with concepts, native source links, and OMOP relationships**,
so that **OMOP concepts are usable as RDF by any standard tool and can later connect to the other vocabularies**.

## Value

OMOP is the base layer of the merged graph and the first format slice of the vocabulary migration.

Migrating it first proves the Maplib template path, the namespace scheme, and the ingest-to-graph flow before a second source is added.

## Prerequisites

- [E01-S07 Ingest versioned vocabulary releases](E01-S07-ingest-versioned-vocabulary-releases.md) for the ingested release directory, the file lookup, and the release-frame validation.

## Scope

### In scope

- Lazy Polars reading of the Athena tab-delimited files with the OMOP-specific reader settings.
- Filtering to the target vocabularies and reading concepts, relationships, and relationship types.
- Shared vocabulary namespaces and native source-concept IRI minting for the OMOP-relevant prefixes.
- The OMOP concept OTTR template and language-tagged literal helper.
- Maplib graph construction for concept nodes, relationship edges, and relationship predicate labels.
- Turtle output plus a provenance sidecar recording the source name, version, and build time.
- A thin `rosetta vocabulary build-omop` command.

### Out of scope

- DHD, LOINC-SNOMED, and SNOMED International builds; those are E01-S09 and E01-S10.
- The shared source-adapter contract, which is extracted in E01-S09 once two adapters exist.
- Graph merge and the omitted-triple count report, which land in E01-S10.
- Content-addressed artifact versions and differences; that is E01-S11.

## Acceptance Criteria

- [ ] GIVEN a synthetic Athena release with concepts in and outside the target vocabularies, WHEN concepts are loaded, THEN only rows whose `vocabulary_id` is in the target set are kept, and only `concept_id`, `concept_name`, `vocabulary_id`, and `concept_code` are selected.
- [ ] GIVEN Athena files that are tab delimited with unescaped double quotes in `concept_name`, WHEN they are read, THEN every column is read as text and no row is split or dropped.
- [ ] GIVEN an 18-digit concept code, WHEN it is read, THEN it is preserved as a string with no precision loss.
- [ ] GIVEN a loaded concept frame, WHEN the graph is built, THEN each concept has a node typed `skos:Concept` with `skos:prefLabel` from `concept_name` as a language-tagged literal and `skos:notation` from `concept_code`.
- [ ] GIVEN a SNOMED, LOINC, RxNorm, ICD10, or ICD10CM concept, WHEN the graph is built, THEN it carries a `skos:exactMatch` to the native source-vocabulary IRI for that code.
- [ ] GIVEN an RxNorm Extension concept, which has no native code namespace, WHEN the graph is built, THEN no `skos:exactMatch` triple is emitted for it and the concept node still exists.
- [ ] GIVEN a concept code containing characters that are illegal in an IRI path, such as a space or an ampersand, WHEN the native IRI is minted, THEN the code is percent-encoded and the graph serialises.
- [ ] GIVEN relationship rows whose endpoints are both in-scope concepts, WHEN the graph is built, THEN each row becomes a triple whose predicate is the OMOP relationship concept IRI, not a hand-picked SKOS predicate.
- [ ] GIVEN relationship rows whose endpoints include an out-of-scope concept, WHEN the graph is built, THEN those rows are excluded.
- [ ] GIVEN relationship types that actually occur between in-scope concepts, WHEN the graph is built, THEN each such predicate node carries a `skos:prefLabel` from `relationship_name`, and unused relationship types get no label triple.
- [ ] GIVEN a concept row with a null optional value, WHEN it is mapped through the concept template, THEN no triple is emitted for that predicate on that row.
- [ ] GIVEN a built graph, WHEN Turtle is written, THEN the file binds the vocabulary prefixes, parses in a process that does not import `plugin_rosetta`, and is accompanied by a provenance sidecar naming the source, version, and build timestamp.
- [ ] GIVEN a release directory with no ingested files, WHEN a build is requested, THEN the error names the missing release directory and the ingest command that fixes it.
- [ ] GIVEN an ingested synthetic release, WHEN `rosetta vocabulary build-omop` runs, THEN it exits 0, writes the Turtle output and sidecar, and the command body contains no graph logic.

## Technical Tasks

- [ ] Add `src/plugin_rosetta/vocabulary/namespaces.py` with the prefix and namespace table, `sct_iri`, `omop_iri`, and `source_concept_iri` including percent-encoding, plus the target-vocabulary set.
- [ ] Add `src/plugin_rosetta/graph/templates.py` with the OMOP concept OTTR template, its IRI, the language-tagged struct field constant, and `language_tagged_column`.
- [ ] Add `src/plugin_rosetta/vocabulary/omop.py` with `load_target_concepts`, `load_relationships`, `load_relationship_types`, and `build_graph`.
- [ ] Validate each loaded Athena frame against its declared table contract from E01-S07 before transforming it.
- [ ] Add `src/plugin_rosetta/graph/io.py` with a Maplib Turtle writer that creates parents and writes atomically.
- [ ] Add the provenance sidecar writer recording source name, source version, format version, and build timestamp.
- [ ] Add `src/plugin_rosetta/application/vocabulary.py` function `build_omop_graph(release_dir, output_dir)`.
- [ ] Add the thin `rosetta vocabulary build-omop` command and a `justfile` recipe.
- [ ] Add `tests/vocabulary/test_omop.py` and `tests/graph/test_templates.py` driven by small in-memory Polars frames and the synthetic fixture release.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/vocabulary/omop.py` `_scan_athena`, `load_target_concepts`, `load_relationships`, `load_relationship_types` | `src/plugin_rosetta/vocabulary/omop.py` | Keep the lazy scan, the tab separator, and the disabled quote character |
| `src/sssom_rosetta/vocabulary/omop.py` `_concept_rows`, `_relationship_rows`, `_relationship_label_rows`, `build_graph` | `src/plugin_rosetta/vocabulary/omop.py` | Keep relationships as OMOP relationship concepts, with self-describing predicate labels |
| `src/sssom_rosetta/vocabulary/omop.py` `build_from_release`, `_exact`, `write_ttl` | `src/plugin_rosetta/vocabulary/omop.py` plus `src/plugin_rosetta/graph/io.py` | Split release location from serialisation |
| `src/sssom_rosetta/vocabulary/namespaces.py` `_NAMESPACES`, `PREFIX_MAP`, `omop_iri`, `source_concept_iri`, `TARGET_VOCABULARIES` | `src/plugin_rosetta/vocabulary/namespaces.py` | DHD-specific helpers follow in E01-S09; RF2-specific behaviour in E01-S10 |
| `src/sssom_rosetta/vocabulary/templates.py` `CONCEPT_TEMPLATE`, `CONCEPT_TEMPLATE_IRI`, `LANG_STRING_FIELD`, `language_tagged_column` | `src/plugin_rosetta/graph/templates.py` | DHD templates follow in E01-S09 |
| `src/sssom_rosetta/vocabulary/pipeline.py` `_write_snapshot_metadata` | `src/plugin_rosetta/vocabulary/provenance.py` | Sidecar behaviour only; the build-target registry is extracted in E01-S09 |
| `src/sssom_rosetta/cli.py` `vocabulary build-omop` (line 627) | `src/plugin_rosetta/application/vocabulary.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to the application function |
| `sssom-rosetta/tests/vocabulary/test_omop.py` | `tests/vocabulary/test_omop.py` | Port the RxNorm Extension, percent-encoding, relationship-predicate, and label assertions |

## Edge Cases

- `CONCEPT.csv` and `CONCEPT_RELATIONSHIP.csv` share a filename prefix, so lookup must match the exact filename.
- Athena files use a `.csv` extension but are tab delimited, which breaks any default CSV reader.
- A relationship type that never occurs between in-scope concepts must not gain a label triple, otherwise the graph grows with unused predicates.
- A production Athena bundle is large, so concept and relationship reads must stay lazy and filter before collecting.
- Null optional template values are silently dropped by Maplib, which is correct here but invisible; the omission count that makes it visible is added in E01-S10.
- A concept name containing a newline must not break the tab-delimited read.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/vocabulary/test_omop.py tests/graph` passes offline against synthetic fixtures.
- [ ] `uv run tara check` passes.
- [ ] `registry/README.md` or the vocabulary documentation records the OMOP IRI scheme and the relationship-predicate decision.
- [ ] The Turtle output parses in a process that does not import `plugin_rosetta`.
- [ ] Acceptance criteria verified with the vocabulary curator on a real ingested Athena release, with only counts and the output path reported.
- [ ] No licensed release payload, extracted file, or generated graph is staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

Do not generalise the adapter yet.

One implementation cannot prove a shared contract, so the extraction waits for DHD in E01-S09.
