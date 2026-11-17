from rdflib import Graph

from plugin_rosetta.ontology.catalog import (
    list_classes,
    list_properties,
    resolve_label,
    resource_exists,
)

PREFIXES = """
@prefix ex: <https://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
"""

ONTOLOGY = f"""{PREFIXES}
ex:Person a owl:Class ;
    rdfs:label "Persoon"@nl, "Person"@en ;
    rdfs:subClassOf ex:Agent .
ex:Place a rdfs:Class ;
    skos:prefLabel "Place"@en .
ex:Unlabelled a owl:Class .
ex:Both a owl:Class ;
    rdfs:label "From rdfs"@en ;
    skos:prefLabel "From skos"@en .
ex:Twin a owl:Class ;
    rdfs:label "Beta"@en, "Alpha"@en .
ex:Plain a owl:Class ;
    rdfs:label "Plain", "Zusatz"@de .
ex:knows a owl:ObjectProperty .
ex:age a owl:DatatypeProperty .
ex:note a owl:AnnotationProperty .
ex:seeAlso a rdf:Property .
"""


def _graph(turtle: str = ONTOLOGY) -> Graph:
    return Graph().parse(data=turtle, format="turtle")


def test_list_classes_returns_sorted_owl_and_rdfs_classes() -> None:
    assert list_classes(_graph()) == [
        "https://example.org/Both",
        "https://example.org/Person",
        "https://example.org/Place",
        "https://example.org/Plain",
        "https://example.org/Twin",
        "https://example.org/Unlabelled",
    ]


def test_list_properties_returns_sorted_property_declarations() -> None:
    assert list_properties(_graph()) == [
        "https://example.org/age",
        "https://example.org/knows",
        "https://example.org/note",
        "https://example.org/seeAlso",
    ]


def test_resolve_label_prefers_rdfs_label_over_skos_pref_label() -> None:
    assert resolve_label(_graph(), "https://example.org/Both") == "From rdfs"


def test_resolve_label_falls_back_to_skos_pref_label() -> None:
    assert resolve_label(_graph(), "https://example.org/Place") == "Place"


def test_resolve_label_applies_the_documented_language_preference() -> None:
    assert resolve_label(_graph(), "https://example.org/Person") == "Person"


def test_resolve_label_prefers_untagged_over_unpreferred_language() -> None:
    assert resolve_label(_graph(), "https://example.org/Plain") == "Plain"


def test_resolve_label_breaks_same_language_ties_lexically() -> None:
    assert resolve_label(_graph(), "https://example.org/Twin") == "Alpha"


def test_resolve_label_is_independent_of_triple_order() -> None:
    reversed_turtle = f"""{PREFIXES}
ex:Person rdfs:label "Person"@en, "Persoon"@nl .
"""
    forward_turtle = f"""{PREFIXES}
ex:Person rdfs:label "Persoon"@nl, "Person"@en .
"""

    assert resolve_label(_graph(reversed_turtle), "https://example.org/Person") == resolve_label(
        _graph(forward_turtle), "https://example.org/Person"
    )


def test_resolve_label_returns_none_when_no_label_exists() -> None:
    assert resolve_label(_graph(), "https://example.org/Unlabelled") is None


def test_resolve_label_returns_none_for_unknown_resource() -> None:
    assert resolve_label(_graph(), "https://example.org/Missing") is None


def test_resource_exists_for_a_declared_subject() -> None:
    assert resource_exists(_graph(), "https://example.org/Person")


def test_resource_exists_for_a_term_used_only_as_an_object() -> None:
    assert resource_exists(_graph(), "https://example.org/Agent")


def test_resource_does_not_exist_for_an_unknown_iri() -> None:
    assert not resource_exists(_graph(), "https://example.org/Missing")
