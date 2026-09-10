# ADR-0001: initialize workspaces from packaged starter registry

- **Status:** Superseded by ADR-0003
- **Date:** 2026-09-10
- **Authors:** @yannick-vinkesteijn, GitHub Copilot

## Context and Problem Statement

The CLI defaults refer to a writable `registry/` in the current workspace, but an installed wheel
does not contain that repository directory. How should a reusable installation provide starter
mapping content and source catalogues without treating user-owned configuration as immutable package
state?

## Considered Options

- Bundle the starter registry as package resources and initialize a selected writable copy.
- Bundle a read-only registry and make commands operate directly on package resources.
- Ship no starter content and require every configuration path explicitly.

## Decision Outcome

Chosen option: bundle the starter registry as package resources and initialize a selected writable
copy with `rosetta init`.

Without explicit selection flags, initialization is interactive and lists mapping sets, ontology
sources, and vocabulary sources separately. Repeatable selection flags provide the non-interactive
path for automation. The resulting `rosetta.yaml` records the selection, while generated
`registry/config/` files contain only the selected entries.

### Consequences

- Good, because an installed wheel can create a working, writable registry without locating a source
  checkout.
- Good, because users choose only the content relevant to their workspace and automation remains
  deterministic through explicit flags.
- Good, because normal commands continue to use plain files under `registry/`; package-resource
  handling stays confined to initialization.
- Bad, because starter resources duplicate the repository's example registry. Tests must compare
  their parsed content to prevent drift.
- Bad, because initialization refuses an existing `rosetta.yaml` or `registry/`; merging and upgrading
  existing workspaces require a future command.
