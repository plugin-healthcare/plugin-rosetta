# E01-S03 Story: read authored CSVW mapping sets

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping curator**,
I want **the authored CSV and CSVW metadata pair to parse into a schema-validated SSSOM mapping set**,
so that **my hand-authored rows are machine-checked before anything is derived from them**.

## Value

The CSV and CSVW pair under `registry/mappings/` is the only hand-authored source of truth.

Reading it correctly, including multivalued columns and preserved values, is the foundation for every derived artifact and every later validation slice.

## Prerequisites

- [E01-S02 Preserve and validate mapping set configuration](E01-S02-preserve-and-validate-mapping-set-configuration.md) for the mapping-set model that supplies `mapping_set_id`, `license`, and `curie_map`.

## Scope

### In scope

- Regenerating the SSSOM Pydantic model from the pinned `sssom-schema` version.
- CURIE expansion with an explicit prefix map.
- CSVW schema conformance checking and CSVW-driven reading of the authored CSV.
- Schema conformance validation of the assembled mapping set.
- A thin `rosetta mapping validate` command that reports schema conformance only.

### Out of scope

- Ontology loading, graph-resolved authoring, and referential integrity; those are E01-S05 and E01-S06.
- Writing SSSOM, Turtle, or reports; that is E01-S04.
- Any Maplib or graph construction.

## Acceptance Criteria

- [ ] GIVEN `registry/mappings/omop-onz-g.csv` and `registry/mappings/omop-onz-g.metadata.json`, WHEN the mapping set is read, THEN it contains exactly 8 mappings in file order.
- [ ] GIVEN the first authored row, WHEN it is read, THEN `subject_id` is `omop:Person`, `predicate_id` is `skos:exactMatch`, `object_id` is `onz-g:PatientInCare`, `confidence` is `0.9`, and `comment` retains its embedded double quotes unchanged.
- [ ] GIVEN a CSVW column declared with `separator: "|"` such as `author_id`, WHEN a row carries a single value, THEN the parsed field is a list with one element rather than a bare string.
- [ ] GIVEN a CSVW column declared with `separator: "|"`, WHEN a row carries two values separated by `|`, THEN the parsed field is a list with two elements.
- [ ] GIVEN the mapping-set configuration, WHEN the mapping set is read, THEN `mapping_set_id`, `license`, and the five-prefix `curie_map` come from the configuration and not from the CSVW metadata document.
- [ ] GIVEN a CSV row that violates the SSSOM schema, WHEN it is read, THEN a schema conformance error is raised that names the offending row index and field, and no mapping set is returned.
- [ ] GIVEN a CSV whose header does not match the CSVW table schema, WHEN it is read, THEN conformance fails before any row is converted to a mapping.
- [ ] GIVEN a row with an empty cell and a row with an absent cell for the same optional column, WHEN they are read, THEN the two are distinguishable in the result or a warning issue is recorded that names the column and row index.
- [ ] GIVEN a CURIE whose prefix is not in the prefix map, WHEN it is expanded, THEN the error names the unknown prefix and lists the known prefixes.
- [ ] GIVEN a value without a `:` separator, WHEN it is expanded as a CURIE, THEN it fails rather than being treated as a bare IRI.
- [ ] GIVEN the tracked mapping set, WHEN `rosetta mapping validate omop-onz-g` runs, THEN it exits 0 and reports 8 conforming rows, and the command body contains no parsing logic.

## Technical Tasks

- [ ] Regenerate `src/plugin_rosetta/mapping/models/sssom.py` from `sssom-schema==1.1.0a5` using the linkml Pydantic generator, and exclude it from lint and formatting the way `sssom-rosetta/pyproject.toml` excludes `src/sssom_rosetta/models/sssom.py`.
- [ ] Add a generation note in the module header recording the schema version and the exact generator command, and state that the file is never hand-edited.
- [ ] Add `src/plugin_rosetta/mapping/curies.py` with `expand_curie` and an unknown-prefix error, backed by `curies` where it removes hand-rolled logic.
- [ ] Add `src/plugin_rosetta/utils/io/csvw.py` with `read_mapping_rows(csv_path, metadata_path)` returning typed row dicts and a conformance check that runs before conversion.
- [ ] Add `src/plugin_rosetta/mapping/validate.py` with `validate_schema_conformance` raising a package schema conformance error.
- [ ] Replace the legacy blanket cell drop with explicit handling: distinguish absent columns from empty strings, and emit a `ValidationIssue` when an empty cell is collapsed to a default.
- [ ] Add `src/plugin_rosetta/mapping/api.py` with `read_mapping_set(key, config_path, root)` composing configuration, CSVW reading, and schema validation.
- [ ] Add the thin `rosetta mapping validate` command over the application function.
- [ ] Add `tests/mapping/test_curies.py`, `tests/io/test_csvw.py`, `tests/mapping/test_validate.py`, and `tests/mapping/test_first_mapping_set.py` covering the preserved eight rows.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/mapping/io.py` `read_mapping_set_csvw` | `src/plugin_rosetta/utils/io/csvw.py` plus `src/plugin_rosetta/mapping/api.py` | Split reading from mapping-set assembly; mapping-set metadata now comes from configuration, not keyword arguments |
| `src/sssom_rosetta/mapping/io.py` empty-cell drop (`if value not in (None, "")`) | `src/plugin_rosetta/utils/io/csvw.py` | Behaviour change: collapsing an empty cell must be reported, not silent |
| `src/sssom_rosetta/mapping/author.py` `expand_curie`, `UnknownPrefixError` | `src/plugin_rosetta/mapping/curies.py` | Graph-free half of `author.py`; `resolve_curie` and `build_mapping` move in E01-S06 |
| `src/sssom_rosetta/mapping/validate.py` `validate_schema_conformance`, `SchemaConformanceError` | `src/plugin_rosetta/mapping/validate.py` | Referential integrity stays behind until E01-S06 |
| `src/sssom_rosetta/models/sssom.py` | `src/plugin_rosetta/mapping/models/sssom.py` | Regenerate from the pin, never copy and hand-edit |
| `sssom-rosetta/tests/mapping/test_io.py`, `tests/mapping/test_first_mapping_set.py` | `tests/io/test_csvw.py`, `tests/mapping/test_first_mapping_set.py` | Port the row-count, CURIE-map, multivalued, and invalid-row assertions |
| `src/sssom_rosetta/cli.py` `_read_and_validate_csvw` (line 132) and `mapping validate` (line 215) | `src/plugin_rosetta/mapping/api.py` plus `src/plugin_rosetta/cli.py` | The shared read-and-validate helper becomes a public feature operation |

## Edge Cases

- The authored `comment` column contains embedded double quotes and non-ASCII characters; parsing must not re-escape or normalise them.
- `confidence` is a CSVW `number`; it must not be read as a string and must not lose precision.
- `reviewer_id` is empty for all eight rows and is multivalued, so the empty-versus-absent rule is exercised by the tracked data itself.
- A CSVW `primaryKey` of `subject_id`, `predicate_id`, `object_id` means duplicate triples must be rejected rather than deduplicated.
- The regenerated model may differ from the legacy generated file; any difference must be reviewed and explained rather than patched by hand.
- `sssom-schema==1.1.0a5` is a pre-release, so the pin must be exact and resolvable in the lock file.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/mapping tests/io` passes.
- [ ] `uv run tara check` passes.
- [ ] The model regeneration command and schema pin are documented in the generated module header and in `registry/README.md`.
- [ ] The authored CSV and CSVW pair remain readable by any standard CSVW tool without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator against the preserved eight rows.
- [ ] No licensed data, cached downloads, or generated artifacts are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

This story stays graph-free on purpose.

Any need for an ontology graph while reading is a signal that work belongs in E01-S06.
