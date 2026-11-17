# Command Line

The `rosetta` command is a thin layer over the Python API.
Each command calls the function of the same feature, so the CLI and your own code follow the same path.
Run `uv run rosetta <group> <command> --help` for the full list of options and defaults.

All commands read their configuration from `registry/config/` and write to `registry/data/` by default.
Use `--config`, `--root`, `--cache-dir`, `--output-dir`, or `--catalog-dir` to point them at another workspace.

## Workspace

| Command | What it does |
| --- | --- |
| `rosetta init [destination]` | Creates `rosetta.yaml`, empty source catalogues, and an ignored `registry/data/` directory. |

## Mapping

| Command | What it does |
| --- | --- |
| `rosetta mapping list` | Lists the configured mapping sets. |
| `rosetta mapping validate <key>` | Checks every row against the SSSOM schema. With `--check-references`, also resolves every `subject_id` and `object_id` against the cached ontologies. |
| `rosetta mapping build <key> --output-dir <dir>` | Writes SSSOM/TSV and RDF/Turtle. Writes nothing when validation fails. Accepts `--check-references`. |
| `rosetta mapping report <key> --output-dir <dir>` | Writes a Markdown and a standalone HTML report. |

## Ontology

| Command | What it does |
| --- | --- |
| `rosetta ontology fetch <name>` | Downloads a configured ontology into `registry/data/ontologies/<name>/<version>/ontology.ttl`, or reuses the cached copy. `--force` downloads again. |

## Vocabulary

| Command | What it does |
| --- | --- |
| `rosetta vocabulary ingest <name> <zip>` | Verifies a manually downloaded release, checks its tables against the table contracts, and caches it under `registry/data/vocabularies/<name>/<version>/`. |
| `rosetta vocabulary build-omop` | Builds `omop.ttl` from an ingested Athena release. |
| `rosetta vocabulary build-dhd-diagnosethesaurus --as-of YYYYMMDD` | Builds the DHD Diagnosethesaurus graph for the given validity date. |
| `rosetta vocabulary build-dhd-verrichtingenthesaurus --as-of YYYYMMDD` | Builds the DHD Verrichtingenthesaurus graph for the given validity date. |
| `rosetta vocabulary build-loinc-snomed` | Builds the LOINC-SNOMED graph from an RF2 release. |
| `rosetta vocabulary build-snomed-international` | Builds the SNOMED CT International graph from an RF2 release. |
| `rosetta vocabulary merge` | Merges every built vocabulary graph into `vocabularies.ttl`. |

Each build also writes a `.meta.json` provenance file next to the graph.

## Artifact

| Command | What it does |
| --- | --- |
| `rosetta artifact register <name> <path> --kind <kind> --source-name <s> --source-version <v>` | Stores an immutable, content-addressed version with a JSON manifest. |
| `rosetta artifact list <name>` | Prints the registered versions as JSON. |
| `rosetta artifact diff <name> <base> <head>` | Prints a typed difference between two versions as JSON. |

## Exit codes

A command exits with code 0 on success.
A known Rosetta error prints one message to standard error and exits with code 1, without a Python traceback.
`rosetta mapping validate` prints every issue it finds and also exits with code 1 when the report contains an error.
