from pathlib import Path

import pytest
from linkml_runtime.utils.metamodelcore import URI
from rdflib import Graph

from plugin_rosetta.application.mapping import read_mapping_set
from plugin_rosetta.core.errors import ValidationError
from plugin_rosetta.io.rdf import write_turtle
from plugin_rosetta.mapping.models.sssom import Mapping, MappingSet

ROOT = Path(__file__).parents[2]


def test_writes_deterministic_parseable_turtle(tmp_path: Path) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=ROOT).mapping_set
    first_path = tmp_path / "first.ttl"
    second_path = tmp_path / "nested/second.ttl"

    write_turtle(mapping_set, first_path)
    write_turtle(mapping_set, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert len(Graph().parse(first_path, format="turtle")) == 8


def test_invalid_mapping_leaves_no_partial_turtle(tmp_path: Path) -> None:
    mapping_set = MappingSet(
        mapping_set_id=URI("https://example.org/mapping"),
        license=URI("https://creativecommons.org/publicdomain/zero/1.0/"),
        curie_map={
            "test": "https://example.org/",
            "semapv": "https://w3id.org/semapv/vocab/",
        },
        mappings=[
            Mapping(
                predicate_id="test:predicate",
                object_id="test:object",
                mapping_justification="semapv:ManualMappingCuration",
            )
        ],
    )
    output_path = tmp_path / "mapping.ttl"

    with pytest.raises(ValidationError, match="subject_id"):
        write_turtle(mapping_set, output_path)

    assert not output_path.exists()
