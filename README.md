# plugin-rosetta

Rosetta is a Python toolbox for authoring, validating, and publishing open mapping artifacts.

## Install

```shell
uv sync --all-groups
uv run rosetta --help
```

## Build mappings

```shell
uv run rosetta mapping validate omop-onz-g
uv run rosetta mapping build omop-onz-g --output-dir registry/data/mappings/omop-onz-g
uv run rosetta mapping report omop-onz-g --output-dir registry/data/mappings/omop-onz-g
```

The build writes SSSOM/TSV and RDF/Turtle artifacts.

The report command writes Markdown and standalone HTML.

All generated files are standard formats that can be read without Rosetta.

## Explore interactively

```shell
just notebook
```

Opens `notebooks/quickstart_nb.py`, a [marimo](https://marimo.io) notebook that reads the `omop-onz-g`
mapping set, inspects it with Polars, and builds the same SSSOM/TSV, Turtle, Markdown, and HTML
artifacts as the CLI commands above.
