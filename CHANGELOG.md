# Changelog

All notable changes to this project are documented here.

## 0.1.0 - 2026-09-10

### Added

- Installable `plugin-rosetta` Python library and `rosetta` command-line interface.
- Mapping validation, SSSOM and Turtle publication, and Markdown and HTML reports.
- Configured ontology download, caching, and referential validation.
- Configured vocabulary ingestion and OMOP, DHD, LOINC-SNOMED, and SNOMED
  International graph builders.
- Deterministic vocabulary graph merging with provenance and optional-value
  omission counts.
- Content-addressed local artifact registration and typed table, SSSOM, and RDF
  differences.

### Changed

- Domain configuration is caller-owned input and is not included as package
  data.
- DHD builds require an explicit validity date.

### Deferred

- Protege, Gephi, OWL-DL classification, FHIR runtime, SQL on FHIR, UI, and
  remote artifact storage.
