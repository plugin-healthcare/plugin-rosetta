# plugin-rosetta

Rosetta is a Python toolbox for authoring, validating, and publishing open mapping artifacts.

## Install

```shell
uv sync --all-groups
uv run rosetta --help
```

After installing the wheel, initialize a writable workspace and select its mapping, ontology, and
vocabulary sources:

```shell
rosetta init my-rosetta-workspace
cd my-rosetta-workspace
```

The interactive command writes the selections to `rosetta.yaml` and creates a filtered `registry/`
from starter resources bundled in the wheel. Automation can bypass the prompts with repeatable
`--mapping-set`, `--ontology-source`, and `--vocabulary-source` options.

## Build mappings

```shell
uv run rosetta mapping validate omop-onz-g
uv run rosetta mapping build omop-onz-g --output-dir registry/data/mappings/omop-onz-g
uv run rosetta mapping report omop-onz-g --output-dir registry/data/mappings/omop-onz-g
```

The build writes SSSOM/TSV and RDF/Turtle artifacts.

The report command writes Markdown and standalone HTML.

All generated files are standard formats that can be read without Rosetta.

## Fetch ontologies

```shell
uv run rosetta ontology fetch omop-cdm
uv run rosetta ontology fetch onz-g
```

Downloads a configured ontology source's Turtle file into `registry/data/ontologies/<name>/<version>/`,
skipping the download if it is already cached. Use `--force` to re-download. See `registry/README.md`
for the source configuration.

## Validate against ontologies

Schema conformance only proves a row is well formed. `--check-references` additionally resolves every
`subject_id` and `object_id` against the ontology bound to it in `registry/config/mapping-sets.yaml`,
which catches a term that was valid when authored but has since been removed or renamed upstream.

```shell
just fetch
uv run rosetta mapping validate omop-onz-g --check-references
uv run rosetta mapping build omop-onz-g --output-dir registry/data/mappings/omop-onz-g --check-references
```

Validation reads the cached ontologies only; it never downloads, and it names the fetch command to run
if the cache is empty rather than skipping the check. `validate` prints every issue and exits non-zero,
and `build` writes no artifact at all when any reference is unresolved.

Labels resolved from an ontology are deterministic. Candidate labels are ordered by predicate
(`rdfs:label` before `skos:prefLabel`), then by language (`en`, then `nl`, then untagged literals, then
any remaining tag alphabetically), then by the label text itself. A term with no label resolves to an
explicit absence, never an empty string.

## Ingest vocabulary releases

Vocabulary releases are licence gated and must be downloaded manually from the page recorded in
`registry/config/vocabulary-sources.yaml`. Ingest verifies a pinned checksum when present and extracts
the release into a versioned, ignored cache:

```shell
uv run rosetta vocabulary ingest omop ~/Downloads/athena-release.zip
# or
just ingest omop ~/Downloads/athena-release.zip
```

If the source has no pinned checksum, the command prints the computed SHA-256 for curator review.
Cached releases with a pinned checksum require the original ZIP on every ingest so extracted files
can be verified against a trusted artifact. Unpinned releases can be reused without the ZIP, using
their local integrity manifest to detect accidental corruption. Use `--force` only when the cached
release must be replaced. See `registry/README.md` for the source catalogue, cache layout, and table
contracts.

## Explore interactively

```shell
just notebook
```

Opens `notebooks/quickstart_nb.py`, a [marimo](https://marimo.io) notebook that reads the `omop-onz-g`
mapping set, inspects it with Polars, and builds the same SSSOM/TSV, Turtle, Markdown, and HTML
artifacts as the CLI commands above.
