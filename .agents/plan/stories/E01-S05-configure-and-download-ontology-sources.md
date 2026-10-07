# E01-S05 Story: configure and download ontology sources

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **mapping curator**,
I want **ontology sources declared in tracked YAML and downloaded reproducibly into a local cache**,
so that **the same pinned bytes back every validation run and a source change is visible in review instead of hidden in Python code**.

## Value

Ontology source definitions currently live in Python globals, so changing a pin means changing code.

Moving them to tracked configuration with pinned version, URL, and checksum makes ontology provenance reviewable and makes validation reproducible offline after the first fetch.

## Prerequisites

- [E01-S01 Establish the installable package and shared contracts](E01-S01-establish-the-installable-package-and-shared-contracts.md) for the error hierarchy and validation report.
- [E01-S02 Preserve and validate mapping set configuration](E01-S02-preserve-and-validate-mapping-set-configuration.md) for the tracked-configuration pattern and the YAML loader.

## Scope

### In scope

- `registry/config/ontology-sources.yaml` as the tracked source catalogue.
- A frozen Pydantic `OntologySource` model with name, version, IRI, download URL, and checksum.
- Reusable download code with checksum verification and cache reuse under `registry/data/ontologies/`.
- Parsing a cached ontology file into an RDF graph.
- A thin `rosetta ontology fetch` command.

### Out of scope

- Label lookup, identifier existence checks, and referential validation; those are E01-S06.
- Licence-gated vocabulary releases, which have no open URL and are handled in E01-S07.
- Any remote or shared cache; the cache is local only.

## Acceptance Criteria

- [ ] GIVEN `registry/config/ontology-sources.yaml`, WHEN it is loaded, THEN it yields the two migrated sources `omop-cdm` version `5.4` and `onz-g` version `2.8.1` with their pinned download URLs and canonical IRIs.
- [ ] GIVEN an unknown source name, WHEN it is looked up, THEN the error lists the known source names.
- [ ] GIVEN a source with a pinned checksum and a stubbed HTTP response whose bytes match, WHEN the source is fetched, THEN the file is written to `registry/data/ontologies/<name>/<version>/ontology.ttl`.
- [ ] GIVEN a source with a pinned checksum and a stubbed HTTP response whose bytes do not match, WHEN the source is fetched, THEN a checksum error names the source, the expected checksum, and the actual checksum, and no cache file is written.
- [ ] GIVEN a source without a pinned checksum, WHEN it is fetched, THEN a validation issue with severity warning is returned that names the source and reports the computed checksum, and the issue is visible in command output rather than only in a log record.
- [ ] GIVEN an already-cached source, WHEN it is fetched again, THEN no HTTP request is made and the cached path is returned.
- [ ] GIVEN an already-cached source, WHEN it is fetched with the force option, THEN the download runs again and replaces the cache atomically.
- [ ] GIVEN an HTTP error or timeout, WHEN a source is fetched, THEN a fetch error names the URL and the underlying cause and no partial file remains in the cache.
- [ ] GIVEN a cached ontology file, WHEN it is loaded, THEN a populated RDF graph is returned and the file is parsed only from the cache.
- [ ] GIVEN a cached file that is not valid Turtle, WHEN it is loaded, THEN the parse error names the cached path.
- [ ] GIVEN the tracked configuration, WHEN `rosetta ontology fetch omop-cdm` runs, THEN it exits 0, prints the cache path and any warning issue, and the command body contains no HTTP or parsing logic.

## Technical Tasks

- [ ] Create `registry/config/ontology-sources.yaml` with the two migrated sources, including the comments that explain why each URL is pinned the way it is.
- [ ] Add `src/plugin_rosetta/ontology/config.py` with a frozen Pydantic `OntologySource` model and a loader that reuses the YAML boundary from E01-S02.
- [ ] Add `src/plugin_rosetta/ontology/download.py` with a reusable `download_to_cache(url, destination, expected_checksum)` helper that is source-type agnostic.
- [ ] Add `src/plugin_rosetta/ontology/loader.py` with `fetch_ontology` and `load_ontology` over the download helper, defaulting the cache root to `registry/data/ontologies`.
- [ ] Write downloads to a temporary file in the destination directory and replace on success so a failed or mismatched download leaves no partial file.
- [ ] Return missing-checksum findings as `ValidationIssue` values on the result instead of logging only.
- [ ] Backfill the pinned checksums for `omop-cdm` and `onz-g` as a reviewed change once a curator confirms the downloaded bytes.
- [ ] Add `src/plugin_rosetta/ontology/api.py` with `fetch_ontology_source(name, config_path, cache_dir, force)`.
- [ ] Add the thin `rosetta ontology fetch` command and a `justfile` recipe that fetches both configured sources.
- [ ] Add `tests/ontology/test_config.py` and `tests/ontology/test_loader.py` with a stubbed HTTP client so tests run offline.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `src/sssom_rosetta/ontology/sources.py` `ONTOLOGY_SOURCES` globals | `registry/config/ontology-sources.yaml` | Source definitions become tracked content; keep the pinned commit SHA and widoco URL comments |
| `src/sssom_rosetta/ontology/sources.py` `OntologySource`, `get_source`, `UnknownOntologySourceError` | `src/plugin_rosetta/ontology/config.py` | Dataclass becomes a frozen Pydantic model for YAML validation |
| `src/sssom_rosetta/ontology/loader.py` `fetch_ontology`, `load_ontology`, `_cache_path` | `src/plugin_rosetta/ontology/loader.py` | Same cache layout, new default root `registry/data/ontologies` |
| `src/sssom_rosetta/ontology/loader.py` missing-checksum `logger.info` branch | `src/plugin_rosetta/ontology/loader.py` | Behaviour change: becomes a reported validation issue |
| `src/sssom_rosetta/ontology/loader.py` `requests.get` | `src/plugin_rosetta/ontology/download.py` | Use the declared HTTP client dependency behind a small helper |
| `src/sssom_rosetta/cli.py` `ontology fetch` (line 104) | `src/plugin_rosetta/ontology/api.py` plus `src/plugin_rosetta/cli.py` | Behaviour moves to the public feature API |
| `sssom-rosetta/justfile` `fetch` recipe | `justfile` | Same two sources, driven by configuration |
| `sssom-rosetta/tests/ontology/test_loader.py`, `tests/ontology/test_sources.py` | `tests/ontology/test_loader.py`, `tests/ontology/test_config.py` | Port cache-hit, force, checksum, and network-error assertions |

## Edge Cases

- The `onz-g` download URL is widoco-generated and is regenerated on every republish, so a 404 must produce a clear fetch error that points at the publication page recorded in the configuration.
- Both migrated sources currently have no pinned checksum, so the warning path is the default path until the backfill lands.
- A cache directory that exists but is empty must be treated as a cache miss.
- A source version string is part of the cache path, so it must be validated as filesystem safe.
- Two configured sources that resolve to the same name must fail at load time rather than overwrite each other.
- `registry/data/` is git-ignored, so tests must never rely on a cache that only exists on the developer machine.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/ontology` passes and makes no network call.
- [ ] `uv run tara check` passes.
- [ ] `registry/README.md` documents the ontology source configuration and the cache layout.
- [ ] Cached ontology files stay in their original Turtle form and are usable by any RDF tool without `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping curator, including the checksum backfill decision.
- [ ] No downloaded ontology payloads or cache contents are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

This story is the first that touches the network, so every test stubs the HTTP client.

The download helper is written to be reusable by E01-S07, but the vocabulary path stays manual because those releases are licence gated.
