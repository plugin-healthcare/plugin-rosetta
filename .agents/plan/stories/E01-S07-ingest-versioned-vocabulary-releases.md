# E01-S07 Story: ingest versioned vocabulary releases

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **vocabulary curator**,
I want **to ingest a manually downloaded licence-gated release ZIP into a versioned local cache with a checksum and a schema check**,
so that **every later graph build runs against verified, reproducible files and never against an ad hoc folder on my machine**.

## Value

The OMOP, DHD, LOINC-SNOMED, and SNOMED International releases are licence gated and cannot be downloaded from an open URL.

Ingest is the controlled entry point that pins what was loaded, verifies it, and keeps licensed payloads out of the repository.

## Prerequisites

- [E01-S05 Configure and download ontology sources](E01-S05-configure-and-download-ontology-sources.md) for the tracked-source configuration pattern and the cache conventions.

## Scope

### In scope

- `registry/config/vocabulary-sources.yaml` as the tracked catalogue of licence-gated releases.
- A frozen Pydantic `VocabularySource` model with name, version, kind, description, download page, checksum, and optional format version.
- Manual local ZIP ingest with checksum verification, idempotent extraction, and force re-extraction.
- Locating exactly one file in an extracted release by prefix, suffix, and path fragment.
- Nyctea-based schema and content validation of tabular release frames.
- Synthetic release fixtures shaped like the real packages.
- A thin `rosetta vocabulary ingest` command.

### Out of scope

- Building any vocabulary graph; that starts in E01-S08.
- Downloading vocabulary releases over HTTP, which the licences do not allow.
- FHIR validation of any kind; Nyctea is used here only for tabular release frames.

## Acceptance Criteria

- [x] GIVEN `registry/config/vocabulary-sources.yaml`, WHEN it is loaded, THEN it yields the four migrated sources `omop`, `dhd-thesauri` with format version `uitleverformaat4.3`, `loinc-snomed`, and `snomed-international`, each with its download page.
- [x] GIVEN an unknown vocabulary source name, WHEN it is looked up, THEN the error lists the known names.
- [x] GIVEN a synthetic release ZIP and a source with a matching pinned checksum, WHEN it is ingested, THEN the archive is extracted under `registry/data/vocabularies/<name>/<version>/` and that directory is returned.
- [x] GIVEN a source with a pinned checksum and a ZIP whose checksum differs, WHEN it is ingested, THEN a checksum error names the source, the expected value, and the actual value, and nothing is extracted.
- [x] GIVEN a source without a pinned checksum, WHEN it is ingested, THEN a warning validation issue reports the computed checksum so a curator can pin it, and the issue is visible in command output.
- [x] GIVEN an already-extracted release, WHEN it is ingested again, THEN extraction is skipped and the cached directory is returned.
- [x] GIVEN an already-extracted release, WHEN it is ingested with the force option, THEN it is re-extracted.
- [x] GIVEN a missing file path or a file that is not a valid ZIP, WHEN it is ingested, THEN an ingest error names the path and the cache is left untouched.
- [x] GIVEN an extracted release, WHEN a file is located by prefix and suffix and exactly one matches, THEN that path is returned.
- [x] GIVEN an extracted release in which zero or more than one file matches, WHEN a file is located, THEN the error lists what was searched for and, for the ambiguous case, every match found.
- [x] GIVEN a release table whose header is missing an expected column, WHEN the release frame is validated, THEN a schema issue names the file and every missing column before any downstream transform runs.
- [x] GIVEN a release table with an unexpected extra column, WHEN the release frame is validated, THEN the extra column is reported as an informational issue and does not fail ingest.
- [x] GIVEN a source declaring a format version, WHEN an ingested release does not carry that format-version marker, THEN ingest fails with an error naming the expected and the found marker.
- [x] GIVEN a synthetic release ZIP, WHEN `rosetta vocabulary ingest omop <zip>` runs, THEN it exits 0, prints the cache directory and any warning issue, and the command body contains no extraction logic.

## Technical Tasks

- [x] Create `registry/config/vocabulary-sources.yaml` from the legacy registry, preserving the version, kind, description, download page, and format-version fields.
- [x] Add `src/plugin_rosetta/vocabulary/config.py` with a frozen Pydantic `VocabularySource` model and lookup that reuses the YAML boundary.
- [x] Add `src/plugin_rosetta/vocabulary/ingest.py` with `cache_dir_for`, `ingest_zip`, and `find_file`, defaulting the cache root to `registry/data/vocabularies`.
- [x] Extract to a temporary directory next to the target and rename on success, so a failed extraction never leaves a half-populated cache directory.
- [x] Reject archive members with absolute paths or parent-directory traversal before extracting.
- [ ] Add `src/plugin_rosetta/vocabulary/frames.py` with Nyctea-backed schema and content validation of a Polars frame against a declared release table contract.
- [x] Declare the expected columns per release table as tracked content under `registry/schemas/` rather than Python constants, so a format change is reviewable.
- [x] Add synthetic fixtures under `tests/fixtures/vocabulary/` that mimic Athena, DHD `uitleverformaat4.3`, and RF2 layouts with a handful of invented rows.
- [x] Add `src/plugin_rosetta/vocabulary/api.py` with `ingest_release(name, zip_path, cache_dir, force)`.
- [x] Add the thin `rosetta vocabulary ingest` command and a `justfile` recipe that wraps it.
- [x] Add `tests/vocabulary/test_config.py`, `tests/vocabulary/test_ingest.py`, and `tests/vocabulary/test_frames.py`.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/vocabulary/sources.py` `VOCABULARY_SOURCES` globals | `registry/config/vocabulary-sources.yaml` | Source definitions become tracked content |
| `src/sssom_rosetta/vocabulary/sources.py` `VocabularySource`, `get_vocabulary_source`, `UnknownVocabularySourceError` | `src/plugin_rosetta/vocabulary/config.py` | The frozen Pydantic model already anticipated a YAML loader |
| `src/sssom_rosetta/vocabulary/fetch.py` `ingest_zip`, `cache_dir_for`, `find_file`, `_is_extracted` | `src/plugin_rosetta/vocabulary/ingest.py` | Same behaviour, new default cache root, plus safe extraction |
| `src/sssom_rosetta/vocabulary/fetch.py` missing-checksum `logger.info` branch | `src/plugin_rosetta/vocabulary/ingest.py` | Behaviour change: becomes a reported validation issue |
| `src/sssom_rosetta/vocabulary/errors.py` `VocabularyError` | `src/plugin_rosetta/errors.py` subclass | Vocabulary errors inherit the package base error added in E01-S01 |
| `src/sssom_rosetta/vocabulary/dhd.py` `_EXPECTED_COLUMNS`, `_scan_dhd` header check, `DhdSchemaError` | `registry/schemas/` plus `src/plugin_rosetta/vocabulary/frames.py` | Manual column checks are replaced by declared contracts validated with Nyctea |
| `src/sssom_rosetta/cli.py` `vocabulary ingest` (line 559) | `src/plugin_rosetta/vocabulary/api.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to the public feature API |
| `sssom-rosetta/justfile` `vocab-ingest` recipe | `justfile` | Same manual-ZIP entry point |
| `sssom-rosetta/tests/vocabulary/test_sources.py` ingest and find-file cases (lines 208 to 243) | `tests/vocabulary/test_ingest.py` | Port extract, idempotence, missing-file, unique, and ambiguous cases |

## Edge Cases

- The `omop` source version is currently the placeholder `unversioned`, so the cache path is not release specific; ingest must warn until a curator pins a real Athena release version.
- RF2 and Athena packages nest files in dated subdirectories, so exact paths cannot be assumed and the ambiguous-match error must list candidates.
- A SNOMED International package ships `Full/`, `Snapshot/`, and `Delta/` copies of the same file names, so the path-fragment filter must be part of the lookup contract from the start.
- A ZIP containing absolute or traversing member paths must be rejected before extraction.
- Extraction of a multi-gigabyte release must stream rather than read the archive into memory.
- Nyctea must run on the release frames only; there is no FHIR resource in this path and no FHIR validation is in scope.
- If Nyctea is unavailable or unpinnable when this story starts, the declared table contracts still land and the check is implemented behind the same interface, so the graph stories are not blocked.

## Definition of Done

- [x] Every new behaviour was driven by a failing test written first.
- [x] `uv run pytest tests/vocabulary` passes offline against synthetic fixtures only.
- [x] `uv run tara check` passes.
- [x] `registry/README.md` documents the vocabulary source configuration, the manual ingest flow, and the cache layout.
- [x] Extracted releases stay in their original published formats and remain usable without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the vocabulary curator on at least one real ingested release, with only the resulting checksum recorded.
- [x] No licensed release payload, extracted file, or real vocabulary row is staged; every committed fixture is synthetic.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

Licensed content never enters the repository.

Fixtures imitate the shape of a release, not its content, and any real identifier used in a fixture must be an invented value.

Nyctea integration was deferred on 2026-09-10 while that library is being refactored. The tracked
contracts and `validate_release_frame` boundary land in this story so the graph-building stories are
not blocked; replacing the compatibility validator with Nyctea remains outstanding.

Required-table filenames, path filters, reader settings, and contract references live in
`vocabulary-sources.yaml`. Graph adapters consume those declarations rather than maintaining a second
source-specific lookup table.
