# E01-S08 OMOP graph handover

## Implemented

- Added configuration-driven lazy Athena reads for `CONCEPT.csv`,
  `CONCEPT_RELATIONSHIP.csv`, and `RELATIONSHIP.csv`.
- Validated every input frame against its E01-S07 table contract before transformation.
- Filtered concepts to the six target vocabularies and relationships to current in-scope endpoints.
- Added shared OMOP, SNOMED CT, LOINC, RxNorm, ICD-10, and ICD-10-CM namespaces with
  percent-encoded native concept IRIs.
- Added the Maplib OTTR concept template with optional label, notation, and native-source triples.
- Kept OMOP relationship concept IRIs as predicates and labelled only predicates used by retained
  relationship rows.
- Added deterministic, atomically written Turtle and an atomic provenance sidecar.
- Added `rosetta vocabulary build-omop`, `just build-omop`, and a synthetic offline walkthrough in
  `notebooks/quickstart_nb.py`.
- Added a clear malformed-row error for physical newlines, which are not representable when Athena
  quote parsing is disabled to preserve unescaped quotes.
- Reorganized the installable package around public `mapping`, `ontology`, and `vocabulary` feature
  APIs. Package errors and reports are available from `plugin_rosetta`, workspace initialization is
  in `plugin_rosetta.workspace`, shared adapters live under `utils/io`, and `py.typed` is packaged.
- Removed unused generic protocols and grouped generic shared code in a `utils/` package with focused
  modules such as `utils/source_names.py`, rather than one catch-all `utils.py`.
- Recorded the feature-oriented public API decision in ADR-0002 and updated completed and future
  migration stories to use the new module paths.

## Validation

- Public API contract tests cover feature imports and the packaged inline-typing marker.
- `uv run marimo check --strict notebooks/quickstart_nb.py` passes.
- `uv run tara check` passes: lint, format, types, 189 tests, and dependency audit.
- A focused code review found one newline-boundary diagnostic gap; it was fixed with a failing
  regression test before this handover.

## Remaining curator check

Run the build against one real, locally ingested Athena release and record only concept,
relationship, and triple counts plus the output path. Do not stage the release or generated graph.

## Start here next

After curator verification and developer commit, E01-S09 builds the DHD diagnosis and procedure
thesaurus graphs and extracts the shared source-adapter contract from the two concrete adapters.
