# E01-S11 Story: compare local artifact versions

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping curator**,
I want **to register produced artifacts as content-addressed local versions and compare a new version with the current one**,
so that **I can see exactly what a source or mapping upgrade changes, and which mappings and graphs it affects, before I use it**.

## Value

Today an upgraded release silently replaces the previous output.

A local catalogue with content-addressed versions and typed differences turns an upgrade into a reviewable change instead of a surprise.

## Prerequisites

- [E01-S10 Build RF2 graphs and merge vocabularies](E01-S10-build-rf2-graphs-and-merge-vocabularies.md), so the mapping and graph formats are stable before versions are recorded.

## Scope

### In scope

- Content-addressed artifact versions computed from canonical artifact bytes.
- Provenance manifests recording artifact kind, source name and version, inputs, checksums, tool version, and build time.
- Local register, list, and diff operations over a tracked-layout catalogue under the ignored data tree.
- Difference slices in order: checksum, schema, keyed row, SSSOM mapping, RDF triple.
- An impact report naming which mappings and graphs depend on a changed source.
- Thin `rosetta artifact register`, `list`, and `diff` commands.

### Out of scope

- Remote or S3-compatible storage, and any storage protocol extraction before the local implementation is tested.
- Aliases, promotion, rollback, catalogue metadata migration, and garbage collection.
- Any change to the artifact formats themselves.

## Acceptance Criteria

- [x] GIVEN a produced artifact file, WHEN it is registered, THEN its version identifier is the checksum of its canonical bytes and re-registering identical content returns the same version without creating a duplicate entry.
- [x] GIVEN two artifacts whose content differs only in whitespace that the canonical form normalises, WHEN both are registered, THEN they resolve to the same version.
- [x] GIVEN a registered artifact, WHEN its manifest is read, THEN it records the artifact kind, the source name and version, the input checksums, the tool version, and the build timestamp.
- [x] GIVEN several registered versions of one artifact, WHEN they are listed, THEN they are returned in a documented, stable order with their registration times.
- [x] GIVEN two versions with different checksums, WHEN they are diffed, THEN the checksum difference is reported first and cheaply, without parsing either artifact.
- [x] GIVEN two tabular versions whose columns differ, WHEN they are diffed, THEN added, removed, and retyped columns are reported and no row comparison is attempted.
- [x] GIVEN two tabular versions with the same schema, WHEN they are diffed, THEN added, removed, and changed rows are reported keyed on the declared key columns.
- [x] GIVEN two SSSOM versions, WHEN they are diffed, THEN added, removed, and changed mappings are reported keyed on subject, predicate, and object.
- [x] GIVEN two RDF versions, WHEN they are diffed, THEN added and removed triples are reported and the comparison uses a plain RDF parser rather than any Rosetta-specific reader.
- [x] GIVEN two RDF versions containing blank nodes, WHEN they are diffed, THEN the behaviour is documented and deterministic rather than reporting spurious differences on every run.
- [x] GIVEN a registered upgrade of a vocabulary source version, WHEN the impact is reported, THEN it names every registered mapping and graph artifact whose manifest lists that source as an input.
- [x] GIVEN an artifact that is not registered, WHEN a diff is requested, THEN the error names the unknown artifact and lists the known ones.
- [x] GIVEN a registered catalogue, WHEN `rosetta artifact register`, `list`, and `diff` run, THEN they exit 0, print machine-readable output, and the command bodies contain no diffing logic.
- [x] GIVEN the catalogue on disk, WHEN it is inspected, THEN manifests are plain JSON that any standard tool can read without importing `plugin_rosetta`.

## Technical Tasks

- [x] Add `src/plugin_rosetta/artifacts/identity.py` computing a content-addressed version from canonical bytes, with the canonicalisation rule documented per artifact kind.
- [x] Add `src/plugin_rosetta/artifacts/manifest.py` with a frozen Pydantic manifest model serialised as plain JSON.
- [x] Add `src/plugin_rosetta/artifacts/catalog.py` with local `register`, `list_versions`, and `resolve` over a directory layout under `registry/data/artifacts/`.
- [x] Add `src/plugin_rosetta/artifacts/diff.py` with checksum, schema, keyed-row, SSSOM mapping, and RDF triple slices.
- [x] Implement RDF triple differences over RDFLib canonical graphs and document deterministic blank-node handling.
- [x] Add an impact query that walks manifests and returns dependent artifacts for a changed input.
- [x] Add a public `src/plugin_rosetta/artifacts/` feature package. Registration remains an explicit operation so normal builds do not create hidden catalogue side effects.
- [x] Add the thin `rosetta artifact` command group and `justfile` recipes.
- [x] Keep storage local without extracting a protocol because no second implementation exists.
- [x] Add focused identity, manifest/catalogue, difference, and CLI tests.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/vocabulary/pipeline.py` `_write_snapshot_metadata` sidecar | `src/plugin_rosetta/artifacts/manifest.py` | The sidecar grows into a full provenance manifest; the sidecar fields stay |
| `src/sssom_rosetta/mapping/report.py` `diff_mapping_sets`, `_mapping_key`, `_differs` | `src/plugin_rosetta/artifacts/diff.py` | The SSSOM diff slice reuses the report's keying rule rather than inventing a second one |
| `sssom-rosetta` `build/` directory convention | `registry/data/artifacts/` | Generated artifacts stay outside version control |

## Edge Cases

- Turtle serialisation is not canonical by default, so an RDF artifact needs a documented canonical form or its content address changes on every rebuild.
- A manifest that records a build timestamp must not feed the content address, otherwise identical content produces different versions.
- Two artifacts of different kinds with identical bytes must remain distinguishable in the catalogue.
- A partially written registration must not leave a manifest without its artifact or an artifact without its manifest.
- A keyed row diff needs declared key columns; a table with no declared key must fail rather than guess.
- A very large graph diff can exhaust memory, so the triple diff must be bounded or streamed and its limits documented.
- The catalogue lives under the ignored data tree, so tests must build their own catalogue in a temporary directory.

## Definition of Done

- [x] Every new behaviour was driven by a failing test written first, one diff slice at a time.
- [x] `uv run pytest tests/artifacts` passes.
- [x] `uv run tara check` passes.
- [x] `README.md` and `registry/README.md` document the catalogue layout, the canonical forms, and the diff slices.
- [x] Manifests and artifacts remain plain open-format files readable without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator by registering and comparing two real versions of one source.
- [x] No licensed data, cached downloads, or generated artifacts are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

Keep this story local and simple.

No storage abstraction, no lifecycle states, and no remote backend until a real second implementation forces the contract.
