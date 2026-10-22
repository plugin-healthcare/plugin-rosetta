# Quickstart

This guide builds the tracked `omop-onz-g` mapping set into SSSOM and RDF files.
It needs Python 3.13 or 3.14, [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

## Install

```shell
uv sync --group dev
```

## Run

```shell
just quickstart
```

The recipe validates the mapping set, builds it, and writes a report.
It needs no network access and no licensed data.
The output goes to `registry/data/mappings/omop-onz-g/`:

| File | Content |
| --- | --- |
| `omop-onz-g.sssom.tsv` | Mappings and metadata in SSSOM/TSV |
| `omop-onz-g.ttl` | The same mappings as RDF/Turtle |
| `omop-onz-g.md` | Mapping report in Markdown |
| `omop-onz-g.html` | The same report as a standalone page |

Warnings about empty `reviewer_id` cells are expected for the current data.

## Read the output

The SSSOM file starts with metadata lines that begin with `#`, followed by one row per mapping.
Each row links a `subject_id` to an `object_id` with a SKOS `predicate_id`, such as `skos:exactMatch` or `skos:broadMatch`.
The columns `mapping_justification`, `confidence`, `author_id`, and `comment` record how and by whom the link was made.

The Turtle file holds one triple per mapping and omits those columns.
The report counts the mappings and the mappings per predicate.

## Check references

```shell
just quickstart-full
```

This downloads the `omop-cdm` and `onz-g` ontologies and checks every `subject_id` and `object_id` against them.
It needs network access.

## Use the Python API

```python
from pathlib import Path

from plugin_rosetta.mapping import build_mapping_artifacts, read_mapping_set, report_mapping_set

result = read_mapping_set("omop-onz-g")
print(len(result.mapping_set.mappings), "mappings,", len(result.report.issues), "warnings")

output_dir = Path("registry/data/mappings/omop-onz-g")
sssom_path, turtle_path = build_mapping_artifacts("omop-onz-g", output_dir=output_dir)
markdown_path, html_path = report_mapping_set("omop-onz-g", output_dir=output_dir)
```

The key `omop-onz-g` is resolved through `registry/config/mapping-sets.yaml`.

## Next steps

Run `just notebook` to explore the same data in a marimo notebook.
Run `uv run rosetta init my-rosetta-workspace` to create an empty workspace, then follow [Onboarding a Standard and Mapping](onboarding.md).
The [command line reference](../reference/cli.md) lists every command.
