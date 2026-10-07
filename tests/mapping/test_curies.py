import pytest

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.mapping.curies import expand_curie

CURIE_MAP = {
    "omop": "https://w3id.org/omop/ontology/",
    "onz-g": "http://purl.org/ozo/onz-g#",
}


def test_expands_known_curie() -> None:
    assert expand_curie("omop:Person", CURIE_MAP) == "https://w3id.org/omop/ontology/Person"


def test_rejects_unknown_prefix() -> None:
    with pytest.raises(ValidationError, match=r"unknown.*Known prefixes: omop, onz-g"):
        expand_curie("unknown:Person", CURIE_MAP)


def test_rejects_value_without_prefix_separator() -> None:
    with pytest.raises(ValidationError, match="not a CURIE"):
        expand_curie("Person", CURIE_MAP)
