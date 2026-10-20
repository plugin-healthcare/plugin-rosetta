# Registry

The `registry/` directory holds the configuration a project owns: which standards it uses, which versions are pinned, and which mappings exist between them.
It never holds the standards themselves, so licensed content stays out of git and every decision is reviewable in a pull request.
The library is generic, and `rosetta init` creates an empty registry ([ADR-0003](../decisions/0003-keep-domain-configuration-outside-the-installed-library.md)).

| Belongs in the registry | Belongs in the library |
| --- | --- |
| `config/` with sources, versions, URLs, and checksums | Readers, validators, builders, and writers |
| `schemas/` with table contracts for releases | The adapters for the Athena, DHD CSV, and RF2 formats |
| `mappings/` with authored mapping sets | Public APIs and CLI commands |
| `data/` with downloads and outputs, ignored by git | Nothing from the registry |

The [configuration reference](../reference/configuration.md) documents every key.
