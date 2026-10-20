# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Documentation site built with Zensical, with a bridge page from known standards to Rosetta concepts, a component overview, a short registry explanation, an onboarding guide for new standards and mapping sets, a capability matrix with the sources under test, and an API reference generated from the docstrings.
- `just docs-serve` and `just docs-build` recipes and a strict documentation build in CI.

### Changed

- Public API docstrings describe arguments, return values, errors, and configuration fields.

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
