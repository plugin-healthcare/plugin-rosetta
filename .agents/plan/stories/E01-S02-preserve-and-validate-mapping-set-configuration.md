# E01-S02 Story: preserve and validate mapping set configuration

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping curator**,
I want **the tracked mapping-set configuration to load into a validated, frozen model that fails fast on bad input**,
so that **mapping identity, licence, file references, and the CURIE map are reviewable content instead of CLI flags I have to retype**.

## Value

In `sssom-rosetta` the mapping-set identifier, licence, file paths, and CURIE map were `justfile` variables passed on every command line.

They are now tracked in `registry/config/mapping-sets.yaml`, and the package must read them as the single source of truth so later stories never take them from ad hoc flags.

## Prerequisites

- [E01-S01 Establish the installable package and shared contracts](E01-S01-establish-the-installable-package-and-shared-contracts.md) for the package layout, error hierarchy, and validation report.

## Scope

### In scope

- A frozen Pydantic configuration model for `registry/config/mapping-sets.yaml`.
- Loading, validating, and looking up a mapping set by key.
- Fail-fast validation of identifiers, licence, referenced files, and CURIE map entries.
- An application function and a thin `rosetta mapping list` command that prints the configured mapping sets.
- Recording the reviewed decisions on `mapping_set_id` and `author_label`.

### Out of scope

- Reading the mapping CSV or CSVW metadata; that is E01-S03.
- Writing any output artifact; that is E01-S04.
- Ontology and vocabulary source configuration; those are E01-S05 and E01-S07.

## Acceptance Criteria

- [ ] GIVEN the tracked `registry/config/mapping-sets.yaml`, WHEN the configuration is loaded, THEN exactly one mapping set `omop-onz-g` is returned with its `mapping_set_id`, `license`, `mapping_file`, `metadata_file`, and five CURIE prefixes (`omop`, `onz-g`, `skos`, `semapv`, `orcid`) preserved byte for byte.
- [ ] GIVEN a loaded mapping-set configuration, WHEN a caller tries to mutate any field, THEN the model raises because it is frozen.
- [ ] GIVEN a configuration file with an unknown field, WHEN it is loaded, THEN a configuration error names the unknown field instead of silently ignoring it.
- [ ] GIVEN a configuration entry whose `mapping_file` or `metadata_file` does not exist relative to the repository root, WHEN it is loaded, THEN a configuration error names the missing path.
- [ ] GIVEN a configuration entry with an empty `curie_map` or a namespace that is not an absolute IRI, WHEN it is loaded, THEN a configuration error names the offending prefix.
- [ ] GIVEN a request for an unknown mapping-set key, WHEN it is looked up, THEN the error lists the known keys.
- [ ] GIVEN the tracked configuration, WHEN `rosetta mapping list` runs, THEN it prints each configured key with its mapping file path and exits 0, and the command body contains no parsing or validation logic.

## Technical Tasks

- [ ] Add `src/plugin_rosetta/mapping/config.py` with frozen `MappingSetConfig` and `MappingSetsConfig` Pydantic models using `model_config = ConfigDict(frozen=True, extra="forbid")`.
- [ ] Add a YAML loader in `src/plugin_rosetta/utils/io/yaml.py` that reads a path and returns a plain mapping, with parse failures raised as a configuration error.
- [ ] Validate `mapping_set_id` and `license` as absolute IRIs and every `curie_map` value as an absolute IRI that ends in `#` or `/`.
- [ ] Resolve `mapping_file` and `metadata_file` relative to a caller-supplied root, defaulting to the current working directory, and verify existence at load time.
- [ ] Add `src/plugin_rosetta/mapping/registry.py` with `list_mapping_sets(config_path, root)` returning plain data.
- [ ] Add the `rosetta mapping list` command in `src/plugin_rosetta/cli.py` as a thin wrapper over the application function.
- [ ] Add `tests/mapping/test_config.py` covering the preserved tracked file plus each failure case with a synthetic YAML file under `tmp_path`.
- [ ] Record the `mapping_set_id` decision: either replace the `sssom-rosetta` build URL with the new canonical identifier and keep the previous value in a documented provenance field, or record in `registry/README.md` that the legacy identifier is deliberately retained.
- [ ] Record the `author_label` decision: either apply the reviewed correction to `registry/mappings/omop-onz-g.csv` in a separate reviewed change, or document in `registry/README.md` that the legacy value is retained for compatibility.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `sssom-rosetta/justfile` variables `mapping_csv`, `mapping_metadata`, `mapping_set_id`, `mapping_license`, `curie_map` (lines 13 to 18) | `registry/config/mapping-sets.yaml` | Already preserved; this story adds the model that reads them |
| `sssom-rosetta/justfile` `validate` and `build` recipes passing `--mapping-set-id`, `--license`, `--curie-map` | `justfile` plus `src/plugin_rosetta/mapping/config.py` | Recipes stop passing mapping-set metadata as flags |
| `src/sssom_rosetta/vocabulary/sources.py` `VocabularySource` (frozen Pydantic model) | `src/plugin_rosetta/mapping/config.py` | Reuse the frozen-model pattern, not the vocabulary content |

## Edge Cases

- The tracked `mapping_set_id` still points at `https://raw.githubusercontent.com/plugin-healthcare/sssom-rosetta/main/build/mappings/omop-onz-g.sssom.tsv`, which is the old build URL; loading must succeed but the decision must be recorded before E01-S04 publishes it.
- A CURIE namespace that does not end in `#` or `/` silently produces wrong IRIs when concatenated, so it must fail at load time.
- A YAML file with duplicate mapping-set keys is resolved silently by most YAML parsers; the loader must detect duplicates and fail.
- A file path that exists but is a directory must fail with the same clarity as a missing path.
- Relative paths in the configuration are repository-root relative, not process-working-directory relative, so tests must prove the behaviour from a different working directory.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/mapping/test_config.py tests/test_cli.py` passes.
- [ ] `uv run tara check` passes.
- [ ] `registry/README.md` documents the configuration shape and the two recorded decisions.
- [ ] `registry/config/mapping-sets.yaml` remains plain YAML that any standard YAML reader can parse without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator, including the `mapping_set_id` and `author_label` decisions.
- [ ] No licensed data, cached downloads, or generated artifacts are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

Preserved mapping values must not change silently.

If the curator approves the `author_label` correction, it lands as its own reviewed change with a before and after diff, not as a side effect of this story.
