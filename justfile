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

notebook:
    uv run marimo edit notebooks/quickstart_nb.py
