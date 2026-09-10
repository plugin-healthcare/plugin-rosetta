# ADR-0002: organize the library around public feature APIs

- **Status:** Accepted
- **Date:** 2026-09-10
- **Authors:** plugin-rosetta maintainers

## Context and Problem Statement

The package initially grouped modules by architectural layer (`application`, `config`, `core`,
`graph`, and `io`). That made command composition clear, but required library users to know internal
layers and import operations such as `plugin_rosetta.application.vocabulary.build_omop_graph`. How
should the package expose a stable, unsurprising Python API while keeping implementation support code
separate?

## Considered Options

- Organize the public API by feature, with `mapping`, `ontology`, and `vocabulary` packages.
- Add a separate `api` package over the existing architectural layers.
- Keep the architectural layers public and document their intended use.

## Decision Outcome

Chosen option: organize the public API by feature. Users navigate by the capability they need, and
the import path remains short:

```python
from plugin_rosetta.mapping import read_mapping_set
from plugin_rosetta.ontology import fetch_ontology_source
from plugin_rosetta.vocabulary import build_omop_graph
```

Package-wide errors and validation reports are exported from `plugin_rosetta`. Workspace
initialization lives in `plugin_rosetta.workspace`. Generic shared implementation code lives in the
`plugin_rosetta.utils` package, grouped into focused modules rather than one `utils.py` file. Feature
`__init__.py` files provide typed lazy exports so public imports do not introduce circular
dependencies between internal modules.

### Consequences

- Good, because public imports describe user intent rather than internal architecture.
- Good, because each feature owns its configuration, operations, and implementation modules.
- Good, because shared utilities have one predictable package without becoming one large module.
- Good, because the packaged `py.typed` marker makes inline type information available downstream.
- Bad, because adding a new public symbol requires maintaining the feature package export list.
- Bad, because lazy exports add a small amount of indirection to feature package initialization.

## Architecture

```text
src/plugin_rosetta/
  __init__.py       # package errors, reports, and version
  py.typed
  errors.py
  reports.py
  workspace.py
  cli.py
  mapping/          # public mapping API and owned implementation
  ontology/         # public ontology API and owned implementation
  vocabulary/       # public vocabulary API and owned implementation
  utils/
    io/             # shared serialization and parsing adapters
    source_names.py # shared portable source-name validation
  resources/        # packaged starter data
```
