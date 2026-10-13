"""Read-only lookups over a loaded ontology graph.

Nothing here fetches or caches data; callers pass in a graph produced by
`ontology.loader`.

Label resolution is deterministic. Candidate labels are ordered by, in
sequence:

1. predicate, `rdfs:label` before `skos:prefLabel`;
2. language, the tags in `LANGUAGE_PREFERENCE` in order, then untagged
   literals, then any remaining tag in alphabetical order;
3. the label text itself, in lexical order.

The first candidate under that order wins, so the same graph always yields
the same label regardless of triple or parse order.
"""

from typing import TYPE_CHECKING

from rdflib import RDF, RDFS, Literal, URIRef
from rdflib.namespace import OWL, SKOS

if TYPE_CHECKING:
    from rdflib import Graph

LANGUAGE_PREFERENCE = ("en", "nl")

_CLASS_TYPES = (OWL.Class, RDFS.Class)
_PROPERTY_TYPES = (
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    RDF.Property,
)
_LABEL_PREDICATES = (RDFS.label, SKOS.prefLabel)


def _declared_subjects(graph: Graph, types: tuple[URIRef, ...]) -> list[str]:
    iris = {
        str(subject)
        for declared_type in types
        for subject in graph.subjects(RDF.type, declared_type)
        if isinstance(subject, URIRef)
    }
    return sorted(iris)


def list_classes(graph: Graph) -> list[str]:
    """Return the sorted IRIs of every `owl:Class` or `rdfs:Class` in the graph."""
    return _declared_subjects(graph, _CLASS_TYPES)


def list_properties(graph: Graph) -> list[str]:
    """Return the sorted IRIs of every property declared in the graph."""
    return _declared_subjects(graph, _PROPERTY_TYPES)


def _language_rank(language: str | None) -> tuple[int, str]:
    if language in LANGUAGE_PREFERENCE:
        # `language` is narrowed to a member of the tuple, so `index` cannot raise.
        return LANGUAGE_PREFERENCE.index(str(language)), ""
    if language is None:
        return len(LANGUAGE_PREFERENCE), ""
    return len(LANGUAGE_PREFERENCE) + 1, language


def resolve_label(graph: Graph, iri: str) -> str | None:
    """Return the preferred label for `iri`, or `None` when the graph has none."""
    subject = URIRef(iri)
    candidates = [
        (predicate_rank, *_language_rank(getattr(label, "language", None)), str(label))
        for predicate_rank, predicate in enumerate(_LABEL_PREDICATES)
        for label in graph.objects(subject, predicate)
        if isinstance(label, Literal)
    ]
    if not candidates:
        return None
    return min(candidates)[-1]


def resource_exists(graph: Graph, iri: str) -> bool:
    """Return whether `iri` appears as a subject or object anywhere in the graph.

    A mapping identifier only has to be something the ontology describes, not a
    declared class or property, so a term used solely as the object of a triple
    still counts as existing.
    """
    resource = URIRef(iri)
    return (resource, None, None) in graph or (None, None, resource) in graph
