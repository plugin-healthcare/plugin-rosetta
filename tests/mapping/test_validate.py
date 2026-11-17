import pytest
from linkml_runtime.utils.metamodelcore import URI
from rdflib import Graph

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.mapping.models.sssom import Mapping, MappingSet
from plugin_rosetta.mapping.validate import (
    validate_referential_integrity,
    validate_schema_conformance,
)
from plugin_rosetta.reports import IssueSeverity

CURIE_MAP = {
    "omop": "https://w3id.org/omop/ontology/",
    "onz-g": "http://purl.org/ozo/onz-g#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "semapv": "https://w3id.org/semapv/vocab/",
    "orcid": "https://orcid.org/",
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


def _mapping_set(*mappings: Mapping) -> MappingSet:
    return MappingSet(
        mapping_set_id=URI("https://example.org/mappings/sample"),
        license=URI("https://creativecommons.org/publicdomain/zero/1.0/"),
        curie_map=CURIE_MAP,
        mappings=list(mappings),
    )


def _mapping(subject_id: str | None = "omop:Person", object_id: str | None = "onz-g:PatientInCare") -> Mapping:
    return Mapping(
        subject_id=subject_id,
        predicate_id="skos:exactMatch",
        object_id=object_id,
        mapping_justification="semapv:ManualMappingCuration",
    )


# --- schema conformance ---


def test_schema_conformance_rejects_a_malformed_row() -> None:
    with pytest.raises(ValidationError, match="row 2"):
        validate_schema_conformance([{"subject_id": "omop:Person", "confidence": "not-a-number"}])


# --- referential integrity ---


def test_resolvable_mappings_produce_a_valid_empty_report(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping()),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert report.issues == ()
    assert report.is_valid


def test_unresolvable_subject_names_row_field_curie_and_iri(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping(subject_id="omop:Gone")),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert not report.is_valid
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.code == "referential.unresolved"
    assert issue.severity is IssueSeverity.ERROR
    assert issue.location == "row 2, column subject_id"
    assert "omop:Gone" in issue.message
    assert "https://w3id.org/omop/ontology/Gone" in issue.message


def test_unresolvable_object_is_checked_against_the_object_graph(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping(object_id="onz-g:Gone")),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert [issue.location for issue in report.issues] == ["row 2, column object_id"]


def test_unknown_prefix_names_the_prefix_and_the_known_prefixes(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping(subject_id="nope:Person")),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.code == "referential.unknown-prefix"
    assert "nope" in issue.message
    assert "Known prefixes" in issue.message


def test_missing_identifiers_are_reported_once_per_field(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping(subject_id=None, object_id=None)),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert [issue.code for issue in report.issues] == ["referential.missing-field"] * 2
    assert [issue.location for issue in report.issues] == ["row 2, column subject_id", "row 2, column object_id"]


def test_row_numbers_follow_the_authored_csv(subject_graph: Graph, object_graph: Graph) -> None:
    report = validate_referential_integrity(
        _mapping_set(_mapping(), _mapping(subject_id="omop:Gone")),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert [issue.location for issue in report.issues] == ["row 3, column subject_id"]


def test_predicates_are_passed_through_without_resolution(subject_graph: Graph, object_graph: Graph) -> None:
    mapping = Mapping(
        subject_id="omop:Person",
        predicate_id="skos:broadMatch",
        object_id="onz-g:PatientInCare",
        mapping_justification="semapv:ManualMappingCuration",
        author_id=["orcid:0000-0001-8979-9194"],
    )

    report = validate_referential_integrity(
        _mapping_set(mapping),
        curie_map=CURIE_MAP,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )

    assert report.issues == ()
