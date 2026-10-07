import pytest
from rdflib import Graph

from plugin_rosetta.errors import UnresolvableCurieError, ValidationError
from plugin_rosetta.mapping.author import build_mapping, resolve_curie

CURIE_MAP = {
    "omop": "https://w3id.org/omop/ontology/",
    "onz-g": "http://purl.org/ozo/onz-g#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "semapv": "https://w3id.org/semapv/vocab/",
}

SUBJECT_TURTLE = """
@prefix omop: <https://w3id.org/omop/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
omop:Person a owl:Class .
"""

OBJECT_TURTLE = """
@prefix onzg: <http://purl.org/ozo/onz-g#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
onzg:PatientInCare a owl:Class .
"""


@pytest.fixture
def subject_graph() -> Graph:
    return Graph().parse(data=SUBJECT_TURTLE, format="turtle")


@pytest.fixture
def object_graph() -> Graph:
    return Graph().parse(data=OBJECT_TURTLE, format="turtle")


def test_resolve_curie_returns_the_expanded_iri(subject_graph: Graph) -> None:
    iri = resolve_curie("omop:Person", CURIE_MAP, subject_graph)

    assert iri == "https://w3id.org/omop/ontology/Person"


def test_resolve_curie_rejects_a_term_absent_from_the_graph(subject_graph: Graph) -> None:
    with pytest.raises(UnresolvableCurieError, match=r"omop:Gone.*w3id.org/omop/ontology/Gone"):
        resolve_curie("omop:Gone", CURIE_MAP, subject_graph)


def test_resolve_curie_rejects_an_unknown_prefix(subject_graph: Graph) -> None:
    with pytest.raises(ValidationError, match="Known prefixes"):
        resolve_curie("nope:Person", CURIE_MAP, subject_graph)


def test_build_mapping_stores_curies_not_expanded_iris(subject_graph: Graph, object_graph: Graph) -> None:
    mapping = build_mapping(
        subject_curie="omop:Person",
        predicate="skos:exactMatch",
        object_curie="onz-g:PatientInCare",
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
        mapping_justification="semapv:ManualMappingCuration",
        confidence=0.9,
        subject_label="Person",
    )

    assert mapping.subject_id == "omop:Person"
    assert mapping.object_id == "onz-g:PatientInCare"
    assert mapping.predicate_id == "skos:exactMatch"
    assert mapping.confidence == 0.9
    assert mapping.subject_label == "Person"


def test_build_mapping_raises_before_constructing_when_the_subject_is_unresolvable(
    subject_graph: Graph,
    object_graph: Graph,
) -> None:
    with pytest.raises(UnresolvableCurieError, match="omop:Gone"):
        build_mapping(
            subject_curie="omop:Gone",
            predicate="skos:exactMatch",
            object_curie="onz-g:PatientInCare",
            curie_map=CURIE_MAP,
            subject_graph=subject_graph,
            object_graph=object_graph,
            mapping_justification="semapv:ManualMappingCuration",
        )


def test_build_mapping_raises_when_the_object_is_unresolvable(subject_graph: Graph, object_graph: Graph) -> None:
    with pytest.raises(UnresolvableCurieError, match="onz-g:Gone"):
        build_mapping(
            subject_curie="omop:Person",
            predicate="skos:exactMatch",
            object_curie="onz-g:Gone",
            curie_map=CURIE_MAP,
            subject_graph=subject_graph,
            object_graph=object_graph,
            mapping_justification="semapv:ManualMappingCuration",
        )
