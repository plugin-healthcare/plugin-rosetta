# Capability Matrix

This matrix records migration status against `sssom-rosetta` revision `46fb077c246388f8c692cdcc6b9129a06f669109`.
Parity means equivalent parsed content, not byte-identical serialization.

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

The machine-readable inventory is `tests/fixtures/parity/workflows.json`.
`tests/test_parity.py` fails when it references a replacement test that no longer exists.

## Sources and test coverage

All tests run offline.
A mocked HTTP client replaces downloads, and small synthetic files that follow the real table layout replace licensed releases.

| Source | Kind | Format | Output | Test data | Real release tested |
| --- | --- | --- | --- | --- | --- |
| `omop-onz-g` | Mapping set | CSV with CSVW | SSSOM/TSV, Turtle, Markdown, HTML | The tracked 8 mappings in `registry/mappings/` | Yes, in the unit tests and the CI quickstart job |
| `omop-cdm` 5.4 | Ontology source | Turtle | Cached graph | Small Turtle graphs in the tests | By hand with `just quickstart-full` only |
| `onz-g` 2.8.1 | Ontology source | Turtle | Cached graph | Small Turtle graphs in the tests | By hand with `just quickstart-full` only |
| `omop` | Vocabulary | `athena`, delimited tables | SKOS Turtle: target concepts, native links, and OMOP relationships | `tests/fixtures/vocabulary/athena/` | No, issue #24 |
| `dhd-thesauri` (DT) | Vocabulary | `dhd-csv`, quoted CSV in uitleverformaat 4.3 | SKOS Turtle: validity windows, preferred labels, SNOMED, ICD-10, and specialty-scoped DBC links | `tests/fixtures/vocabulary/dhd/` | No, issue #24 |
| `dhd-thesauri` (VT) | Vocabulary | `dhd-csv`, quoted CSV in uitleverformaat 4.3 | SKOS Turtle: validity windows, preferred labels, and SNOMED links | `tests/fixtures/vocabulary/dhd/` | No, issue #24 |
| `loinc-snomed` | Vocabulary | `rf2` snapshot | SKOS, RDFS, and OWL Turtle: active concepts, labels, synonyms, and is-a hierarchy | `tests/fixtures/vocabulary/rf2/` | No, issue #24 |
| `snomed-international` | Vocabulary | `rf2` English snapshot | SKOS, RDFS, and OWL Turtle: active concepts, labels, synonyms, and is-a hierarchy | `tests/fixtures/vocabulary/rf2/` | No, issue #24 |

The synthetic fixtures cover edge cases such as 18-digit SNOMED CT identifiers, inactive rows, blank end dates, and DBC codes that are unique only per specialty.
They do not prove that a real release has the columns, sizes, or values that the contracts expect.
Issues #24 and #26 track the comparison of real releases with `sssom-rosetta`.

Other tools read each published format back: `sssom-py` (`parse_sssom_table`) for SSSOM/TSV, RDFLib for Turtle, the Python standard library for JSON, and PyYAML for YAML.
Markdown and HTML reports are checked on their content.

CI runs on Ubuntu with uv. `uv run tara check` runs on Python 3.13 (the minimum) and 3.14; `just quickstart` with the quickstart notebook and `zensical build --strict` run on Python 3.14.
macOS, Windows, and other Python versions are not tested.

## Approved migration differences

| Date | Difference | Reason |
| --- | --- | --- |
| 2026-09-10 | DHD builds require `--as-of YYYYMMDD`. | An explicit effective date makes validity filtering reproducible. |
| 2026-09-10 | Physical release filenames are configuration-owned. | The installed library must not embed one publisher's release naming. |
| 2026-09-10 | Mapping documentation pages are portable Markdown and HTML reports. | A dedicated project-site generator is not a reusable library concern. |
| 2026-09-10 | `mapping_set_id` and authored `author_label` values remain unchanged. | Changing published identity or attribution requires separate curator approval. |

These entries document engineering decisions.
Final curator approval for licensed-release output comparisons remains a release gate.

## Deferred behaviour

| Legacy capability | Status | Reason |
| --- | --- | --- |
| Protege combined OWL export | Deferred | Not required for open mapping publication and intentionally outside E01. |
| Gephi ontology export | Deferred | Visualization exports are outside the reusable library scope. |
| Gephi vocabulary export | Deferred | Visualization exports are outside the reusable library scope. |
| OWL-DL classification, relationship groups, and post-coordination | Deferred | The migrated RF2 graphs intentionally provide lightweight SKOS and RDFS semantics. |
| FHIR runtime, SQL on FHIR, Ariadne, UI, and remote storage | Deferred | Explicitly outside the E01 toolbox scope. |
| SPARQL queries and Jelly serialization (`notebooks/sparql.py`, jelly-maplib plan) | Deferred | Not part of the reusable library yet, and no replacement exists. |
| Benchmark scripts | Deferred | Performance comparisons are not required for the first release. |
| OMOP exploration notebook (`notebooks/omop.py`) | Deferred | Replaced for now by the quickstart notebook. |
| `just clean` | Deferred | Generated output lives under the untracked `registry/data/`. |

## New in plugin-rosetta

| Capability | Replacement |
| --- | --- |
| Empty caller-owned workspace | `rosetta init <workspace>` |
| List configured mapping sets | `rosetta mapping list` |
| Reference checks against cached ontologies | `rosetta mapping validate <key> --check-references` |
| Content-addressed artifact catalogue with manifests and diffs | `rosetta artifact` |
| Offline quickstart that runs in CI | `just quickstart` and the [quickstart](../guides/quickstart.md) |
