# E01-S06 Story: validate mappings against ontology catalogs

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping curator**,
I want **every mapping subject and object checked against the ontology it claims to come from**,
so that **a term that was removed or renamed upstream is caught before the mapping set is published**.

## Value

Schema conformance only proves a row is well formed.

Referential validation is what catches drift: a mapping that was valid when authored but whose term no longer exists after the ontology was re-fetched.

## Prerequisites

- [E01-S04 Write open mapping artifacts and reports](E01-S04-write-open-mapping-artifacts-and-reports.md) for the published artifacts that must not be produced from an invalid set.
- [E01-S05 Configure and download ontology sources](E01-S05-configure-and-download-ontology-sources.md) for the loaded ontology graphs.

## Scope

### In scope

- Read-only catalog queries over a loaded ontology graph: class listing, property listing, deterministic label resolution, and resource existence.
- Ontology-resolved mapping authoring that resolves both CURIEs before constructing a mapping.
- Referential integrity validation of an existing mapping set against configured subject and object ontologies.
- Binding each mapping-set CURIE prefix to the ontology source that must resolve it.
- Failing the build before any output is written when referential validation fails.

### Out of scope

- Vocabulary releases and graph pipelines; those start in E01-S07.
- Reasoning, OWL classification, or inference of any kind.
- New output formats; the report from E01-S04 gains referential issues but no new artifact type.

## Acceptance Criteria

- [ ] GIVEN the cached `omop-cdm` and `onz-g` ontology fixtures, WHEN the preserved `omop-onz-g` mapping set is validated, THEN all 8 subject identifiers resolve against the OMOP graph and all 8 object identifiers resolve against the ONZ-G graph, and the report is valid.
- [ ] GIVEN a mapping whose `subject_id` is not present in the subject graph, WHEN the set is validated, THEN one issue is reported naming the row index, the field, the CURIE, and the expanded IRI.
- [ ] GIVEN a mapping whose CURIE prefix is not in the mapping-set `curie_map`, WHEN the set is validated, THEN one issue is reported naming the unknown prefix and the known prefixes.
- [ ] GIVEN a mapping with a missing `subject_id` or `object_id`, WHEN the set is validated, THEN one issue is reported per missing field rather than an exception.
- [ ] GIVEN a mapping set with at least one referential issue, WHEN a build is requested, THEN no SSSOM/TSV or Turtle output file is written.
- [ ] GIVEN an ontology graph in which a term carries several labels in different languages, WHEN its label is resolved twice in separate processes, THEN the same label is returned both times according to a documented preference order.
- [ ] GIVEN an ontology graph in which a term carries no label, WHEN its label is resolved, THEN the result is an explicit absence and not an empty string.
- [ ] GIVEN a subject and object CURIE that both resolve, WHEN a mapping is authored through the ontology-resolved path, THEN the constructed mapping stores the CURIEs, not the expanded IRIs.
- [ ] GIVEN a subject CURIE that does not resolve, WHEN a mapping is authored through the ontology-resolved path, THEN it raises before the mapping is constructed.
- [ ] GIVEN the tracked configuration, WHEN `rosetta mapping validate omop-onz-g --check-references` runs, THEN it exits non-zero if any referential issue exists, prints every issue, and the command body contains no graph logic.

## Technical Tasks

- [ ] Add `src/plugin_rosetta/ontology/catalog.py` with `list_classes`, `list_properties`, `resolve_label`, and `resource_exists` over an RDF graph.
- [ ] Make `resolve_label` deterministic: sort candidate labels by a documented language preference, then by lexical order, and document the preference in the module docstring.
- [ ] Add `src/plugin_rosetta/mapping/author.py` with `resolve_curie` and `build_mapping` that resolve subject and object against their graphs before constructing a mapping.
- [ ] Extend `src/plugin_rosetta/mapping/validate.py` with `validate_referential_integrity` returning `ValidationIssue` values on the shared report type instead of a module-local issue dataclass.
- [ ] Add a mapping-set to ontology binding in `registry/config/mapping-sets.yaml`: which configured ontology source validates subjects and which validates objects.
- [ ] Extend `src/plugin_rosetta/mapping/api.py` so validation and build load the bound ontologies and refuse to write output when the report is invalid.
- [ ] Add the `--check-references` option to `rosetta mapping validate` and wire the same guard into `rosetta mapping build`.
- [ ] Add `tests/ontology/test_catalog.py`, `tests/mapping/test_author.py`, and referential cases in `tests/mapping/test_validate.py`, all driven by small synthetic Turtle fixtures.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/ontology/catalog.py` `list_classes`, `list_properties`, `resource_exists` | `src/plugin_rosetta/ontology/catalog.py` | Behaviour preserved |
| `src/sssom_rosetta/ontology/catalog.py` `resolve_label` | `src/plugin_rosetta/ontology/catalog.py` | Behaviour change: the legacy "first one encountered" is nondeterministic and must become a documented preference order |
| `src/sssom_rosetta/mapping/author.py` `resolve_curie`, `build_mapping`, `UnresolvableCurieError` | `src/plugin_rosetta/mapping/author.py` | The graph-resolved half of `author.py`, deferred from E01-S03 |
| `src/sssom_rosetta/mapping/validate.py` `validate_referential_integrity`, `validate_mapping_set`, `ReferentialIntegrityIssue`, `ValidationResult` | `src/plugin_rosetta/mapping/validate.py` plus `src/plugin_rosetta/reports.py` | Issue and result types collapse into the shared report |
| `src/sssom_rosetta/cli.py` `mapping validate` ontology-graph wiring (lines 215 to 269) | `src/plugin_rosetta/mapping/api.py` | Graph loading moves out of the CLI |
| `sssom-rosetta/tests/mapping/test_validate.py`, `tests/mapping/test_author.py`, `tests/ontology/test_catalog.py` | `tests/mapping/test_validate.py`, `tests/mapping/test_author.py`, `tests/ontology/test_catalog.py` | Port the resolution and issue assertions, add the determinism case |

## Edge Cases

- The mapping-set `curie_map` includes `skos`, `semapv`, and `orcid`, which are not ontology terms to resolve; only subject and object identifiers are checked, and predicates are passed through.
- A term that appears only as the object of a triple still exists in the ontology, so existence must consider both subject and object positions.
- An ontology that fails to load must produce a clear error rather than a validation report full of false negatives.
- A mapping-set entry that binds a prefix to an ontology source that is not configured must fail at configuration load time.
- Multiple labels in the same language must still resolve deterministically, which the lexical tiebreak covers.
- Running validation without a populated cache must instruct the curator to fetch the ontology rather than silently skipping the check.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/mapping tests/ontology` passes and makes no network call.
- [ ] `uv run tara check` passes.
- [ ] `README.md` documents the ontology-backed validation step and the label preference order.
- [ ] Published artifacts are unchanged in format and remain readable without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator against the preserved mapping set and both real ontologies.
- [ ] No ontology payloads or cache contents are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

This story closes the mapping half of the migration.

Everything after it is about vocabularies, graphs, and artifact comparison.
