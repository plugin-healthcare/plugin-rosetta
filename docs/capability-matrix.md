# Migration capability matrix

This matrix records migration status against `sssom-rosetta` revision
`46fb077c246388f8c692cdcc6b9129a06f669109`. Parity means equivalent parsed
content, not byte-identical serialization.

## Retained workflows

| Legacy workflow | Replacement | Evidence | Status |
| --- | --- | --- | --- |
| Fetch configured ontologies | `rosetta ontology fetch <name>` | `tests/test_cli.py::test_ontology_fetch_writes_path_and_warnings` | Migrated |
| Validate mappings | `rosetta mapping validate <key>` | `tests/test_cli.py::test_mapping_validate_reports_conforming_rows` | Migrated |
| Build SSSOM and Turtle | `rosetta mapping build <key> --output-dir <dir>` | `tests/test_parity.py::test_preserved_mapping_build_has_legacy_semantics` | Migrated |
| Render mapping reports | `rosetta mapping report <key> --output-dir <dir>` | `tests/mapping/test_report.py::test_report_renders_predicate_counts_as_markdown_and_html` | Migrated |
| Generate mapping documentation pages | `rosetta mapping report <key> --output-dir <dir>` | `tests/mapping/test_report.py::test_report_renders_predicate_counts_as_markdown_and_html` | Folded into portable Markdown and HTML reports |
| Ingest licensed vocabulary releases | `rosetta vocabulary ingest <name> <zip>` | `tests/test_cli.py::test_vocabulary_ingest_command_extracts_synthetic_release` | Migrated |
| Build OMOP | `rosetta vocabulary build-omop` | `tests/test_cli.py::test_vocabulary_build_omop_writes_graph_and_sidecar` | Migrated |
| Build DHD DT and VT | `rosetta vocabulary build-dhd-* --as-of YYYYMMDD` | `tests/test_cli.py::test_vocabulary_build_dhd_commands_write_graph_and_sidecar` | Migrated with explicit validity date |
| Build LOINC-SNOMED RF2 | `rosetta vocabulary build-loinc-snomed` | `tests/test_cli.py::test_vocabulary_build_rf2_commands_write_graph_and_sidecar` | Migrated |
| Build SNOMED International RF2 | `rosetta vocabulary build-snomed-international` | `tests/test_cli.py::test_vocabulary_build_rf2_commands_write_graph_and_sidecar` | Migrated |
| Merge vocabulary graphs | `rosetta vocabulary merge` | `tests/vocabulary/test_merge.py::test_merge_turtle_files_uses_maplib_and_writes_atomic_union` | Migrated |

The machine-readable inventory is
`tests/fixtures/parity/workflows.json`. `tests/test_parity.py` fails when it
references a replacement test that no longer exists.

## Published formats

| Format | Producer | Independent reader |
| --- | --- | --- |
| SSSOM/TSV | Mapping build | `sssom-py` and Rosetta round-trip tests |
| RDF/Turtle | Mapping and vocabulary builds | RDFLib subprocess tests |
| Markdown | Mapping report | Plain UTF-8 text |
| HTML | Mapping report | Standalone HTML content tests |
| JSON | Provenance and artifact manifests | Python standard-library JSON tests |
| YAML | Caller-owned configuration | PyYAML boundary tests |

## Migrated vocabulary sources

| Source | Input | Output | Scope |
| --- | --- | --- | --- |
| OMOP Athena | Configured delimited tables | SKOS Turtle | Target concepts, native links, and OMOP relationships |
| DHD Diagnosethesaurus | Quoted CSV release | SKOS Turtle | Validity windows, preferred labels, SNOMED, ICD-10, and specialty-scoped DBC links |
| DHD Verrichtingenthesaurus | Quoted CSV release | SKOS Turtle | Validity windows, preferred labels, and SNOMED links |
| LOINC-SNOMED | RF2 snapshot | SKOS, RDFS, and OWL Turtle | Active concepts, labels, synonyms, and is-a hierarchy |
| SNOMED International | English RF2 snapshot | SKOS, RDFS, and OWL Turtle | Active concepts, labels, synonyms, and is-a hierarchy |

## Approved migration differences

| Date | Difference | Reason |
| --- | --- | --- |
| 2026-09-10 | DHD builds require `--as-of YYYYMMDD`. | An explicit effective date makes validity filtering reproducible. |
| 2026-09-10 | Physical release filenames are configuration-owned. | The installed library must not embed one publisher's release naming. |
| 2026-09-10 | Mapping documentation pages are portable Markdown and HTML reports. | A dedicated project-site generator is not a reusable library concern. |
| 2026-09-10 | `mapping_set_id` and authored `author_label` values remain unchanged. | Changing published identity or attribution requires separate curator approval. |

These entries document engineering decisions. Final curator approval for
licensed-release output comparisons remains a release gate.

## Deferred behavior

| Legacy capability | Status | Reason |
| --- | --- | --- |
| Protege combined OWL export | Deferred | Not required for open mapping publication and intentionally outside E01. |
| Gephi ontology export | Deferred | Visualization exports are outside the reusable library scope. |
| Gephi vocabulary export | Deferred | Visualization exports are outside the reusable library scope. |
| OWL-DL classification, relationship groups, and post-coordination | Deferred | The migrated RF2 graphs intentionally provide lightweight SKOS and RDFS semantics. |
| FHIR runtime, SQL on FHIR, Ariadne, UI, and remote storage | Deferred | Explicitly outside the E01 toolbox scope. |
