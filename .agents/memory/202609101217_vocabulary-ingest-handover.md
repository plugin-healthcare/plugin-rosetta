# E01-S07 vocabulary ingest handover

## Branch

Work continues on `feature/rosetta-foundation-mapping`.

The original E01-S07 increment is committed as `8115ec4`. The subsequent full-review fixes and
workspace initializer are not committed or pushed.

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
- Added an integrity manifest so cache hits recheck the ingested archive identity and every extracted
  file instead of trusting a populated directory. Pinned sources require the original ZIP and derive
  expected member checksums from it; unpinned sources can reuse the writable manifest only as an
  accidental-corruption check.
- Added exact filename matching for Athena tables, including `CONCEPT.csv`,
  `CONCEPT_RELATIONSHIP.csv`, and `RELATIONSHIP.csv`.

## Full checkpoint review

A complete branch review was run before E01-S08. It found and fixed:

- vocabulary and ontology source-name traversal outside configured cache roots;
- checksum bypasses on ontology and vocabulary cache hits;
- partial mapping builds when Turtle rendering failed after SSSOM had already been written;
- ambiguous Athena table matching and repeated scans for required-column null counts;
- installed-wheel defaults that depended on a source checkout.

The installed-wheel decision is recorded in
`docs/decisions/0001-initialize-workspaces-from-packaged-starter-registry.md`. `rosetta init` now
lists selectable mapping sets, ontology sources, and vocabulary sources interactively, supports
repeatable flags for automation, writes `rosetta.yaml`, and generates a filtered writable registry
from package resources.

## Nyctea decision

Nyctea is actively being refactored and is not pinned in this increment. `validate_release_frame`
provides the planned contract boundary and currently checks columns, Polars data types, and required
values directly. Replace that implementation with Nyctea once its refactor stabilizes; do not expose
Nyctea types through the public application or CLI interfaces.

## Validation state

- `uv run tara check` passes: lint, format, types, 170 tests, and dependency audit.
- Focused source, ingest, frame, and CLI tests pass entirely offline.
- The test fixtures contain invented identifiers and release-shaped rows only.
- A wheel installed into a clean virtual environment from outside the checkout successfully ran
  `rosetta init` and validated all 8 preserved mapping rows from the generated workspace.

## Remaining

- Verify ingest against one real curator-provided release and record only its checksum, never its
  payload or rows.
- Replace the compatibility frame validator with Nyctea after its refactor stabilizes.

## Start here next

E01-S08 builds the OMOP vocabulary graph from the ingested Athena release. Reuse
`find_file`, load `omop-concept.yaml`, and validate the release frame before any graph transform.
