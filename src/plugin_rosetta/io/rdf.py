"""Deterministic RDF mapping output."""

from typing import TYPE_CHECKING

from rdflib import Graph, URIRef

from plugin_rosetta.core.errors import ValidationError
from plugin_rosetta.io._atomic import atomic_write_text
from plugin_rosetta.mapping.curies import expand_curie

if TYPE_CHECKING:
    from pathlib import Path

    from plugin_rosetta.mapping.models.sssom import MappingSet


def mapping_set_to_graph(mapping_set: MappingSet) -> Graph:
    """Convert each complete mapping into one RDF triple."""
    graph = Graph()
    curie_map = {str(prefix): str(namespace) for prefix, namespace in (mapping_set.curie_map or {}).items()}
    for prefix, namespace in curie_map.items():
        graph.bind(prefix, URIRef(namespace))
    for subject, predicate, object_ in _expanded_triples(mapping_set, curie_map):
        graph.add((URIRef(subject), URIRef(predicate), URIRef(object_)))
    return graph


def write_turtle(mapping_set: MappingSet, destination: Path) -> None:
    """Write stable Turtle without relying on graph iteration order."""
    atomic_write_text(destination, render_turtle(mapping_set))


def render_turtle(mapping_set: MappingSet) -> str:
    """Render stable Turtle without writing it."""
    curie_map = {str(prefix): str(namespace) for prefix, namespace in (mapping_set.curie_map or {}).items()}
    triples = _expanded_triples(mapping_set, curie_map)
    lines = [f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in sorted(curie_map.items())]
    lines.extend(f"<{subject}> <{predicate}> <{object_}> ." for subject, predicate, object_ in sorted(triples))
    return "\n".join(lines) + "\n"


def _expanded_triples(
    mapping_set: MappingSet,
    curie_map: dict[str, str],
) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    for index, mapping in enumerate(mapping_set.mappings or [], start=1):
        if not mapping.subject_id or not mapping.predicate_id or not mapping.object_id:
            raise ValidationError(f"Mapping {index} has no subject_id, predicate_id, or object_id")
        triples.append(
            (
                expand_curie(mapping.subject_id, curie_map),
                expand_curie(mapping.predicate_id, curie_map),
                expand_curie(mapping.object_id, curie_map),
            )
        )
    return triples
