# ADR-0003: Keep domain configuration outside the installed library

- **Status:** Proposed
- **Date:** 2026-09-10
- **Authors:** @yannick-vinkesteijn, GitHub Copilot

## Context and Problem Statement

ADR-0001 placed a copy of the repository's healthcare-specific registry under
`src/plugin_rosetta/resources/` so `rosetta init` could scaffold it from an installed wheel.
These files are user input rather than library implementation. How can the library initialize a
workspace without implying that one domain registry is required or canonical?

## Considered Options

- Bundle the healthcare registry in the wheel as starter package data.
- Keep healthcare configuration in the repository's top-level `registry/` and initialize an empty
  workspace from the wheel.
- Remove workspace initialization and require users to create every file manually.

## Decision Outcome

Chosen option: keep healthcare configuration in the top-level `registry/` and initialize an empty
workspace, because the reusable library must not depend on or distribute one project's source
catalogues, mappings, and validation contracts as runtime package data.

### Consequences

- Good, because installed library APIs work exclusively from paths and configuration supplied by
  callers.
- Good, because the wheel no longer duplicates project-specific mappings, catalogues, and schemas.
- Good, because `rosetta init` still creates the minimal writable file layout needed to begin.
- Bad, because a newly initialized workspace is not immediately able to build the repository's
  healthcare examples.
- Bad, because users must copy or author the source definitions and contracts appropriate to their
  project.
