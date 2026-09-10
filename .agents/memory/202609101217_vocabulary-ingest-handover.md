# E01-S07 vocabulary ingest handover

## Branch

Work continues on `feature/rosetta-foundation-mapping`.

Nothing in this increment has been staged, committed, or pushed.

## Implemented

- Added the tracked four-source catalogue at `registry/config/vocabulary-sources.yaml`.
- Added frozen Pydantic source models and strict configuration loading.
- Added streaming SHA-256 verification and safe ZIP extraction into
  `registry/data/vocabularies/<name>/<version>/`.
- Extraction rejects absolute paths, parent traversal, backslash traversal, and symbolic links.
- Extraction is prepared in a sibling temporary directory and only replaces the target after the
  archive has passed checksum, format-marker, and member-path validation.
- Required tables are located and checked against their tracked contracts before a newly extracted
  directory is promoted into the cache.
- Added idempotent cache reuse, forced replacement, and deterministic release-file lookup.
- Added tracked Athena, DHD, and RF2 table contracts plus synthetic release-shaped fixtures.
- Added the `rosetta vocabulary ingest` command and `just ingest` wrapper.

## Nyctea decision

Nyctea is actively being refactored and is not pinned in this increment. `validate_release_frame`
provides the planned contract boundary and currently checks columns, Polars data types, and required
values directly. Replace that implementation with Nyctea once its refactor stabilizes; do not expose
Nyctea types through the public application or CLI interfaces.

## Validation state

- `uv run tara check` passes: lint, format, types, 134 tests, and dependency audit.
- Focused source, ingest, frame, and CLI tests pass entirely offline.
- The test fixtures contain invented identifiers and release-shaped rows only.

## Remaining

- Verify ingest against one real curator-provided release and record only its checksum, never its
  payload or rows.
- Replace the compatibility frame validator with Nyctea after its refactor stabilizes.

## Start here next

E01-S08 builds the OMOP vocabulary graph from the ingested Athena release. Reuse
`find_file`, load `omop-concept.yaml`, and validate the release frame before any graph transform.
