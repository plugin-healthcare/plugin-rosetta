# E01-S04 Story: write open mapping artifacts and reports

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping consumer**,
I want **the authored mapping set to be published as SSSOM/TSV, RDF/Turtle, and a readable report**,
so that **I can use the mappings with standard tooling and review changes without installing `plugin-rosetta`**.

## Value

Derived artifacts are the product of this toolbox.

They must be deterministic, complete, and readable by tools that know SSSOM, Turtle, and Markdown, with no Rosetta dependency and no partial files after a failure.

## Prerequisites

- [E01-S03 Read authored CSVW mapping sets](E01-S03-read-authored-csvw-mapping-sets.md) for the validated mapping set.

## Scope

### In scope

- SSSOM/TSV writing with the YAML metadata header and `|`-joined multivalued cells.
- RDF/Turtle writing of one triple per mapping with bound prefixes.
- Reading a generated SSSOM/TSV back into a mapping set.
- Mapping-set differences and Markdown and HTML report rendering.
- Optional generated documentation pages from the same renderer.
- Thin `rosetta mapping build` and `rosetta mapping report` commands.
- Atomic writes so invalid input never leaves partial output files.

### Out of scope

- Ontology-resolved validation; that is E01-S06.
- Content-addressed artifact versions, manifests, and registered differences; that is E01-S11.
- Gephi and Protege exports, which are deferred for this release.

## Acceptance Criteria

- [ ] GIVEN the validated `omop-onz-g` mapping set, WHEN SSSOM/TSV is written, THEN the file starts with a `#`-prefixed YAML header carrying `mapping_set_id`, `license`, and `curie_map`, and contains 8 data rows plus one header row.
- [ ] GIVEN a mapping with a multivalued field such as `author_id`, WHEN SSSOM/TSV is written, THEN the cell is a single `|`-joined string, not a Python list repr.
- [ ] GIVEN the same mapping set, WHEN SSSOM/TSV is written twice, THEN both files are byte identical.
- [ ] GIVEN the validated mapping set, WHEN Turtle is written, THEN it contains exactly 8 triples whose subject, predicate, and object are the CURIEs expanded through the configured `curie_map`.
- [ ] GIVEN the written Turtle, WHEN it is parsed by a plain RDFLib process that does not import `plugin_rosetta`, THEN parsing succeeds and the triple count matches.
- [ ] GIVEN the written SSSOM/TSV, WHEN it is read by a plain `sssom-py` process that does not import `plugin_rosetta`, THEN it parses and yields 8 rows.
- [ ] GIVEN a generated SSSOM/TSV, WHEN it is read back, THEN `|`-joined multivalued cells become lists again and missing cells do not become the string `nan`.
- [ ] GIVEN a base and a head mapping set, WHEN they are diffed, THEN added, removed, and changed rows are reported keyed on `subject_id`, `predicate_id`, `object_id`.
- [ ] GIVEN no base mapping set, WHEN a diff is rendered, THEN every mapping appears as added.
- [ ] GIVEN a rendered Markdown report, WHEN it is converted to HTML, THEN the tables survive and the predicate counts match the mapping set.
- [ ] GIVEN an output directory that does not exist, WHEN artifacts are written, THEN parent directories are created.
- [ ] GIVEN a mapping set that fails validation, WHEN a build is attempted, THEN no output file exists afterwards, including no zero-length or partially written file.
- [ ] GIVEN the tracked configuration, WHEN `rosetta mapping build omop-onz-g` and `rosetta mapping report omop-onz-g` run, THEN both exit 0 and the command bodies contain no serialisation logic.

## Technical Tasks

- [ ] Add `src/plugin_rosetta/utils/io/sssom.py` with `write_sssom_tsv` and `read_sssom_tsv` over `sssom-py`'s `MappingSetDataFrame`, `write_tsv`, and `parse_sssom_table`.
- [ ] Add `src/plugin_rosetta/utils/io/rdf.py` with `mapping_set_to_graph` and `write_turtle`, binding every configured prefix on the graph.
- [ ] Implement writes atomically: write to a temporary file inside the destination directory and replace on success, so a failure leaves no partial file.
- [ ] Add `src/plugin_rosetta/mapping/report.py` with `diff_mapping_sets`, `predicate_counts`, `render_markdown`, and `render_html`.
- [ ] Derive the multivalued field list from the generated model fields rather than a hardcoded list, matching the legacy `_LIST_FIELDS` approach.
- [ ] Fold the legacy documentation-page generator into the report module as an optional output rather than a separate module.
- [ ] Add `src/plugin_rosetta/mapping/api.py` functions `build_mapping_artifacts` and `report_mapping_set` returning written paths.
- [ ] Add the thin `rosetta mapping build` and `rosetta mapping report` commands, plus `justfile` recipes that wrap them.
- [ ] Add an independent-reader test that runs a subprocess with only `rdflib` and `sssom-py` imported and asserts the outputs parse.
- [ ] Add `tests/io/test_sssom.py`, `tests/io/test_rdf.py`, and `tests/mapping/test_report.py`.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/mapping/io.py` `write_sssom_tsv`, `_mapping_row` | `src/plugin_rosetta/utils/io/sssom.py` | Keep the `|`-join and `None`-drop behaviour |
| `src/sssom_rosetta/mapping/io.py` `mapping_set_to_graph`, `write_ttl` | `src/plugin_rosetta/utils/io/rdf.py` | Keep one triple per mapping; do not reify mapping metadata in this release |
| `src/sssom_rosetta/mapping/report.py` `load_mapping_set_tsv`, `_parse_list_cell`, `_is_nan` | `src/plugin_rosetta/utils/io/sssom.py` `read_sssom_tsv` | Reading belongs at the I/O boundary, not in the report module |
| `src/sssom_rosetta/mapping/report.py` `diff_mapping_sets`, `predicate_counts`, `render_markdown`, `render_html` | `src/plugin_rosetta/mapping/report.py` | Keep the diff and render split |
| `src/sssom_rosetta/mapping/docs_pages.py` | `src/plugin_rosetta/mapping/report.py` | Folded in as an optional documentation output, not a separate module |
| `src/sssom_rosetta/cli.py` `mapping build` (line 270), `mapping report` (line 322), `docs generate-mapping-pages` (line 367) | `src/plugin_rosetta/mapping/api.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to public feature operations |
| `sssom-rosetta/justfile` `build`, `report`, `docs-pages` recipes | `justfile` | Recipes become thin wrappers with no mapping metadata flags |
| `sssom-rosetta/tests/mapping/test_io.py`, `tests/mapping/test_report.py`, `tests/mapping/test_docs_pages.py` | `tests/io/test_sssom.py`, `tests/io/test_rdf.py`, `tests/mapping/test_report.py` | Port the header, triple, diff, and render assertions |

## Edge Cases

- A pandas `NaN` in a missing TSV cell must not reach the model as a float or the string `nan`.
- A mapping missing `subject_id` or `object_id` cannot produce a triple and must fail before writing, not mid-serialisation.
- Turtle serialisation ordering must be stable so repeated builds do not produce spurious differences.
- The Markdown report must escape pipe characters in cell values such as `|`-joined author lists so tables do not break.
- The HTML report must not embed absolute local paths, which would leak the developer environment into a published artifact.
- Writing into a directory the process cannot create must fail with a clear error and leave nothing behind.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/io tests/mapping` passes.
- [ ] `uv run tara check` passes.
- [ ] `README.md` documents the build and report commands, and the generated outputs are described in `registry/README.md`.
- [ ] SSSOM/TSV, Turtle, Markdown, and HTML outputs are proven readable by standard tools in a process that does not import `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator on the published `omop-onz-g` artifacts.
- [ ] Generated artifacts stay under the ignored `registry/data/` tree and are not staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

This story closes the graph-free mapping slice.

After it, the preserved mapping set is fully round-trippable without any ontology being available.
