# E01-S06 ontology-backed validation handover

## Branch

Work continues on `feature/rosetta-foundation-mapping`.

Nothing in this increment has been staged, committed, or pushed. The branch is still ahead of
`origin/feature/rosetta-foundation-mapping` by the E01-S05 commit (`9744b60`).

## Implemented: E01-S06 validate mappings against ontology catalogs

Ported from `sssom-rosetta`'s `ontology/catalog.py`, `mapping/author.py`, and `mapping/validate.py`
onto this repo's conventions: the shared `ValidationIssue`/`ValidationReport` replace the legacy
module-local `ReferentialIntegrityIssue`/`ValidationResult`, and graph loading moved out of the CLI
into the application layer.

### New files

- `src/plugin_rosetta/ontology/catalog.py` — `list_classes`, `list_properties`, `resolve_label`,
  `resource_exists` over an `rdflib.Graph`. `resource_exists` deliberately accepts a term used only
  as the object of a triple, since a mapping identifier only has to be something the ontology
  describes.
- `src/plugin_rosetta/mapping/author.py` — `resolve_curie` and `build_mapping`, the graph-resolved
  half of `author.py` deferred from E01-S03. Reuses the existing `mapping/curies.py::expand_curie`
  rather than reintroducing the legacy expansion helper. The predicate is passed through unresolved.

### Behaviour change: deterministic label resolution

The legacy `resolve_label` returned "the first one encountered", which is nondeterministic across
processes. Candidates are now ordered by predicate (`rdfs:label` before `skos:prefLabel`), then
language (`LANGUAGE_PREFERENCE = ("en", "nl")`, then untagged literals, then any remaining tag
alphabetically), then the label text lexically. The order is documented in the module docstring and
in `README.md`. A term with no label resolves to `None`, never `""`.

### Changed files

- `src/plugin_rosetta/core/errors.py` — added `UnresolvableCurieError(ValidationError)`, keeping the
  error hierarchy in one place instead of defining it inside `author.py` as the legacy code did.
- `src/plugin_rosetta/mapping/validate.py` — added `validate_referential_integrity`, returning a
  `ValidationReport` with codes `referential.missing-field`, `referential.unknown-prefix`, and
  `referential.unresolved`. Rows are numbered from `FIRST_MAPPING_ROW = 2` so a reported row number
  points at the line in the authored CSV that the curator has to edit; issue locations use the same
  `row N, column X` shape the CSVW reader already emits.
- `src/plugin_rosetta/config/mapping_sets.py` — added the frozen `MappingSetOntologies` model and an
  optional `ontologies` field. `load_mapping_sets` takes an optional `ontology_sources` argument;
  when supplied, every binding is resolved at load time so an unconfigured source fails there rather
  than halfway through validation. The binding stays optional, so mapping sets without one still
  load and only fail if reference checking is actually requested.
- `registry/config/mapping-sets.yaml` — bound `omop-onz-g` subjects to `omop-cdm` and objects to
  `onz-g`.
- `src/plugin_rosetta/ontology/loader.py` — extracted `_parse_turtle` and added
  `load_cached_ontology`, which never touches the network and names the exact
  `rosetta ontology fetch <name>` command when the cache is empty, so validation can never silently
  skip the check.
- `src/plugin_rosetta/application/mapping.py` — `read_mapping_set` gained `check_references`,
  `ontology_config_path`, and `cache_dir`. The bound graphs are loaded *before* the CSV is read, so
  a missing binding or empty cache fails fast. `build_mapping_artifacts` refuses to write when the
  report is invalid, which is now a general invariant: **build never writes from an invalid report**,
  not just from a referential one.
- `src/plugin_rosetta/cli.py` — `--check-references`, `--ontology-config`, and `--cache-dir` on
  `mapping validate` and `mapping build`. `validate` prints every issue and exits 1 when the report
  is invalid. Command bodies contain no graph logic.
- `justfile` — added `just validate` (`--check-references`).
- `README.md` — new "Validate against ontologies" section documenting the workflow and the label
  preference order.

### Scope call: CLI error presentation

E01-S06 introduces two failure paths a curator will hit routinely (empty cache, unbound mapping set),
and both surfaced as raw rich tracebacks. Added a small `_guard` helper in `cli.py` that turns any
`RosettaError` into `error: <message>` on stderr with exit code 1, and applied it uniformly to all
five commands rather than only the two new paths. This is slightly wider than the story's technical
tasks; flag it in review if it should be split out.

## Validation state

`uv run tara check` is fully green: lint, format, types, 98 tests, and `uv audit`.

`uv run pytest tests/mapping tests/ontology` passes and makes no network call. Every new test is
driven by small synthetic Turtle fixtures. Two shared fixtures live in `tests/conftest.py`:
`ontology_cache` (declares exactly the 8 OMOP and 8 ONZ-G terms the preserved set references) and
`drifted_ontology_cache` (the same cache with `omop:Vocabulary` removed).

New test files: `tests/ontology/test_catalog.py`, `tests/mapping/test_author.py`,
`tests/mapping/test_validate.py`, `tests/application/test_mapping.py`; plus binding cases in
`tests/config/test_mapping_sets.py` and four CLI cases in `tests/test_cli.py`.

## Verified against the real ontologies

After `just fetch` (both sources cached, checksums still unpinned):

- `rosetta mapping validate omop-onz-g --check-references` exits 0; all 8 subjects resolve against
  the real OMOP graph and all 8 objects against the real ONZ-G graph.
- Renaming `omop:Vocabulary` in a throwaway copy of the real OMOP Turtle produced exactly one issue,
  `row 9, column subject_id`, naming the CURIE and the expanded IRI, and exit code 1.
- `mapping build --check-references` against that drifted cache exited 1 and left the output
  directory empty; the same command against the intact cache wrote both artifacts.
- An empty cache printed
  `error: Ontology 'omop-cdm' is not cached at ... Run: rosetta ontology fetch omop-cdm`, exit 1,
  no traceback.
- `resolve_label` on the real graphs returns `Cliënt`, `Zorgverlener`, and `Dood` for the ONZ-G
  terms (that ontology carries `@nl` labels only) and `Person` for `omop:Person`, matching the
  `object_label`/`subject_label` values in the authored CSV.

No ontology payload is staged: `registry/data/.gitignore` ignores everything but the README.

## Start here next

1. Review the S06 diff and decide how it should be layered for the stacked PR (foundation + notebook,
   ontology sources, ontology-backed validation).
2. Push the E01-S05 commit and open the stacked PRs; nothing has been pushed since `9744b60`.
3. E01-S07 ingest versioned vocabulary releases is next; everything after S06 is vocabularies,
   graphs, and artifact comparison.

## Known follow-up points, carried forward

- Checksums for `omop-cdm` and `onz-g` are still unpinned; backfilling needs a curator to confirm
  the downloaded bytes. The values computed on this machine were
  `e9124408b61d5a95f5bcc4a2d4798a96f3e1f75002631c200a98d537613f32ce` (omop-cdm) and
  `dce23ba924b49e0aee383755f4ea2e03d99508671b1ee10556e543779993b027` (onz-g).
- `mapping report` does not take `--check-references`; reports are diagnostic, so they stay readable
  for an invalid set. Confirm that is the intended behaviour.
- `pyproject.toml` still has the placeholder project description.
- `registry/README.md`'s regeneration command still does not reproduce the manual `URI` import
  workaround.
