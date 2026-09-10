set shell := ["bash", "-cu"]

install:
    uv sync --all-groups

test:
    uv run pytest

lint:
    uv run ruff check .

format:
    uv run ruff format .

typecheck:
    uv run ty check .

check:
    uv run tara check

build mapping_set="omop-onz-g":
    uv run rosetta mapping build {{mapping_set}} --output-dir registry/data/mappings/{{mapping_set}}

# Validate a mapping set against its bound ontologies; requires `just fetch` first.
validate mapping_set="omop-onz-g":
    uv run rosetta mapping validate {{mapping_set}} --check-references

report mapping_set="omop-onz-g":
    uv run rosetta mapping report {{mapping_set}} --output-dir registry/data/mappings/{{mapping_set}}

# Fetch and cache both configured ontology sources (omop-cdm, onz-g).
fetch:
    uv run rosetta ontology fetch omop-cdm
    uv run rosetta ontology fetch onz-g

ingest vocabulary="omop" archive:
    uv run rosetta vocabulary ingest {{vocabulary}} {{archive}}

build-omop:
    uv run rosetta vocabulary build-omop

build-dhd-diagnosethesaurus as_of:
    uv run rosetta vocabulary build-dhd-diagnosethesaurus --as-of {{as_of}}

build-dhd-verrichtingenthesaurus as_of:
    uv run rosetta vocabulary build-dhd-verrichtingenthesaurus --as-of {{as_of}}

build-loinc-snomed:
    uv run rosetta vocabulary build-loinc-snomed

build-snomed-international:
    uv run rosetta vocabulary build-snomed-international

merge-vocabularies:
    uv run rosetta vocabulary merge

artifact-register name path kind source_name source_version:
    uv run rosetta artifact register {{name}} {{path}} --kind {{kind}} --source-name {{source_name}} --source-version {{source_version}}

artifact-list name:
    uv run rosetta artifact list {{name}}

artifact-diff name base head:
    uv run rosetta artifact diff {{name}} {{base}} {{head}}

notebook:
    uv run marimo edit notebooks/quickstart_nb.py
