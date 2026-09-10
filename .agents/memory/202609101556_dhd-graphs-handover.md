# E01-S09 DHD graph handover

## Completed

- Added validated, text-only DHD CSV loading in `vocabulary/adapters/thesaurus.py` with strict
  calendar dates and per-table as-of filtering.
- Added deterministic Dutch-first FSN labels, deduplicated SNOMED mappings, ICD-10 derivations,
  and specialty-scoped DBC identifiers.
- Added separate DT and VT namespaces, Maplib templates, deterministic Turtle, and provenance with
  the explicit as-of date.
- Added the shared OMOP and DHD build-adapter contract plus thin Python and Typer entry points.
- Moved source-specific OMOP and thesaurus code under `vocabulary/adapters/` and added semantic table
  roles so configured filenames and path patterns can change without code edits.
- Added offline synthetic DT and VT fixtures, contract tests, CLI tests, and a runnable Marimo
  example.
- Removed healthcare-specific starter resources from `src/`. `rosetta init` now creates empty
  catalogues; the repository's top-level `registry/` remains project input and a working example.
- Added ADR-0003, which supersedes ADR-0001, and updated the epic, migration plan, S01, S09, README,
  and registry documentation.

## Validation

- `uv run tara check` passes with 195 tests.
- `uv run marimo check --strict notebooks/quickstart_nb.py` passes.
- The wheel contains the DHD adapters and `py.typed`, and contains no `plugin_rosetta/resources/`.
- A focused review found and fixed strict source-date validation and missing-language label
  handling.

## Remaining release gate

- Run DT and VT against one licensed local DHD release and record only counts and output paths.
- Do not stage the release, extracted data, or generated graphs.
- The developer reviews and commits; the agent does not commit or push.
