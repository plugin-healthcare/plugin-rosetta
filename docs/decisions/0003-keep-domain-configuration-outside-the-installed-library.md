# ADR-0003: Keep domain configuration outside the installed library

- **Status:** Accepted
- **Date:** 2026-09-10
- **Decision-makers:** @yannick-vinkesteijn

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

### Project and framework

The library is the framework.
It contains the feature APIs, the schemas and contracts that describe the formats, and the mechanisms to read a registry.
A project owns its configuration, its mapping data and its registry.
The intended end state is that mapping-specific code, such as project transformations, also lives in the project, which imports `plugin-rosetta` and does not add that code to the library.
Today such code is still written inside the library, because the extension point for it does not exist yet.
The boundary and the extension point are an open decision, tracked in #29.
