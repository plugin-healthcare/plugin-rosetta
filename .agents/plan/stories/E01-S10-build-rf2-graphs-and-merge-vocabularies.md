# E01-S10 Story: build RF2 graphs and merge vocabularies

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **vocabulary curator**,
I want **the LOINC-SNOMED and SNOMED International RF2 releases built into graphs and every vocabulary graph merged into one open RDF file**,
so that **concepts from different sources connect through shared identifiers in a single artifact any RDF tool can read**.

## Value

RF2 completes the source coverage and merge is what makes the separate graphs useful together.

This story also makes template behaviour observable by reporting how many triples were omitted because optional input values were null.

## Prerequisites

- [E01-S09 Build the DHD thesaurus graphs](E01-S09-build-the-dhd-thesaurus-graphs.md) for the shared adapter contract, namespaces, and templates.

## Scope

### In scope

- RF2 tab-separated readers with the RF2-specific settings and the active-row filter.
- Is-a edges, preferred terms, and synonyms derived from RF2 snapshot files.
- The LOINC-SNOMED extension graph and the SNOMED International backbone graph.
- Snapshot-only and English-file constraints for International packages.
- Merging vocabulary Turtle files into one combined output with bound prefixes.
- Consolidated namespace and template behaviour, including a count of triples omitted because an optional value was null.
- Thin `rosetta vocabulary build-loinc-snomed`, `build-snomed-international`, and `merge` commands.

### Out of scope

- OWL-DL logical definitions, relationship groups, post-coordination, and refsets beyond the language refset.
- Content-addressed artifact versions and differences; that is E01-S11.
- Any visualisation export.

## Acceptance Criteria

- [x] GIVEN an RF2 file containing unescaped double and single quotes in terms, WHEN it is read, THEN every column is text and no row is split or dropped.
- [x] GIVEN an 18-digit concept identifier, WHEN it is read, THEN it is preserved as a string with no overflow or precision loss.
- [x] GIVEN rows with mixed active flags, WHEN active rows are selected, THEN only rows flagged active are kept.
- [x] GIVEN a relationship table, WHEN is-a edges are derived, THEN only active rows with the is-a type identifier are kept, and each becomes both a subclass triple and a broad-match triple from child to parent.
- [x] GIVEN description and language refset tables, WHEN preferred terms are derived, THEN only active preferred synonym rows from the configured dialect are used and each concept gets a language-tagged preferred label and matching RDFS label.
- [x] GIVEN a description table containing non-preferred synonyms, WHEN synonyms are derived, THEN each becomes a language-tagged alternative label and the preferred synonym is not duplicated.
- [x] GIVEN a synthetic LOINC-SNOMED release, WHEN the graph is built, THEN each active concept is typed both as a SKOS concept and an OWL class in the shared SNOMED namespace.
- [x] GIVEN a synthetic SNOMED International release that ships full, snapshot, and delta trees and several language files, WHEN the graph is built, THEN only the configured snapshot English files and language refset are read.
- [x] GIVEN an OMOP graph and a LOINC-SNOMED graph that reference the same SNOMED identifier, WHEN they are merged, THEN the merged graph connects them through one shared node.
- [x] GIVEN a LOINC-SNOMED extension graph and a SNOMED International backbone graph, WHEN they are merged, THEN extension concepts reach the backbone hierarchy.
- [x] GIVEN several Turtle files, WHEN they are merged, THEN the merged output binds the shared prefixes, contains the union of triples with duplicates collapsed, and is written atomically.
- [x] GIVEN a merge over a large input, WHEN it runs, THEN it uses the Maplib read and write path rather than a pure Python parse.
- [x] GIVEN a mapping of rows through any template with optional parameters, WHEN the graph is built, THEN the build result reports, per template and per optional parameter, how many triples were omitted because the value was null.
- [x] GIVEN a build in which every optional value is populated, WHEN the omission report is produced, THEN it reports zero omissions rather than an empty or missing report.
- [x] GIVEN no built vocabulary graphs on disk, WHEN merge is requested, THEN it fails naming the expected inputs rather than writing an empty file.
- [x] GIVEN built graphs, WHEN each RF2 build command and `rosetta vocabulary merge` run, THEN they exit 0 and the command bodies contain no graph logic.

## Technical Tasks

- [x] Add `src/plugin_rosetta/vocabulary/adapters/rf2.py` with configured RF2 reading and shared graph semantics.
- [x] Register LOINC-SNOMED and SNOMED International through one configured RF2 adapter rather than duplicating source modules.
- [x] Constrain International lookup to configured Snapshot English files and a configured language refset identifier.
- [x] Extend shared adapter contract tests to cover both RF2 sources.
- [x] Add `src/plugin_rosetta/vocabulary/merge.py` with a file-based Maplib merge and an in-memory merge for tests that need triple-level assertions.
- [x] Surface complete OMOP, DHD, and RF2 optional-value omission counts in provenance sidecars.
- [x] Add the three thin CLI commands and `justfile` recipes.
- [x] Add mirrored adapter, merge, API, CLI, omission, and cross-graph tests.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/vocabulary/rf2.py` | `src/plugin_rosetta/vocabulary/rf2.py` | Keep the tab separator, disabled quote character, and text-only schema |
| `src/sssom_rosetta/vocabulary/loinc_snomed.py` `build_graph`, `build_from_release`, `write_ttl` | `src/plugin_rosetta/vocabulary/loinc_snomed.py` | Keep the RDFLib construction path; only OMOP and DHD use Maplib templates |
| `src/sssom_rosetta/vocabulary/snomed_international.py` `build_from_release` and its snapshot and English filters | `src/plugin_rosetta/vocabulary/snomed_international.py` | Keep the delegation to the LOINC-SNOMED builder |
| `src/sssom_rosetta/vocabulary/merge.py` `merge_ttl_files`, `merge_graphs`, `_iter_triples` | `src/plugin_rosetta/vocabulary/merge.py` | Keep Maplib for the file path and the rdflib path for in-memory assertions |
| `src/sssom_rosetta/vocabulary/pipeline.py` `merge_candidates` | `src/plugin_rosetta/vocabulary/adapters/__init__.py` | Derive merge inputs from the adapter registry, not a second hardcoded list |
| `src/sssom_rosetta/cli.py` `vocabulary build-loinc-snomed` (line 605), `build-snomed-international` (line 616), `merge` (line 660) | `src/plugin_rosetta/vocabulary/api.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to the public feature API |
| `sssom-rosetta/justfile` `vocab-build-loinc-snomed`, `vocab-merge`, `vocab-build` recipes | `justfile` | Keep RF2 builds opt-in and out of the default build |
| `sssom-rosetta/tests/vocabulary/test_loinc_snomed.py`, `test_snomed_international.py`, `test_merge.py` | matching `tests/` modules | Port the snapshot-constraint, cross-graph connection, and Maplib merge-path assertions |

## Edge Cases

- International RF2 packages ship full, snapshot, and delta copies with identical file-name prefixes, so an unconstrained lookup matches several files and must fail rather than pick one.
- A language refset row that is active but not preferred must not become a preferred label.
- A concept present in the extension but absent from the backbone leaves a dangling parent reference, which is expected and must not fail the build.
- Merging graphs built by different libraries must produce identical triples regardless of which library wrote the input file.
- Duplicate triples across inputs must collapse, and the merged file must not depend on input order.
- A production merge is memory heavy, so the file path must stream through Maplib rather than materialise an rdflib graph.
- The omission count must distinguish a null optional value from a template parameter that was never supplied.

## Definition of Done

- [x] Every new behaviour was driven by a failing test written first.
- [x] `uv run pytest tests/vocabulary` passes offline against synthetic fixtures.
- [x] `uv run tara check` passes.
- [x] The vocabulary documentation records the RF2 scope limits, the merge behaviour, and how omission counts are reported.
- [x] The merged Turtle output parses in a process that does not import `plugin_rosetta`.
- [ ] Acceptance criteria verified with the vocabulary curator on real ingested releases, with only counts and output paths reported.
- [x] No licensed release payload, extracted file, or generated graph is staged; every committed fixture is synthetic.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

This story completes the migrated source coverage.

OWL-DL classification stays out of scope; the graphs are lightweight SKOS and RDFS by design.
