"""Author SSSOM mappings, checking CURIEs against ontology graphs.

Callers supply the prefix map and, for each side, the graph the CURIE must
resolve against.
"""

from typing import TYPE_CHECKING, Any

from plugin_rosetta.errors import UnresolvableCurieError
from plugin_rosetta.mapping.curies import expand_curie
from plugin_rosetta.mapping.models.sssom import Mapping
from plugin_rosetta.ontology.catalog import resource_exists

if TYPE_CHECKING:
    from collections.abc import Mapping as MappingData

    from rdflib import Graph


def resolve_curie(curie: str, curie_map: MappingData[str, str], graph: Graph) -> str:
    """Expand `curie` and verify the result is a resource `graph` describes.

    Raises:
        ValidationError: If the CURIE is malformed or its prefix is unknown.
        UnresolvableCurieError: If the expanded IRI is absent from `graph`.
    """
    iri = expand_curie(curie, curie_map)
    if not resource_exists(graph, iri):
        raise UnresolvableCurieError(curie, iri)
    return iri


def build_mapping(
    *,
    subject_curie: str,
    predicate: str,
    object_curie: str,
    curie_map: MappingData[str, str],
    subject_graph: Graph,
    object_graph: Graph,
    mapping_justification: str,
    **extra_fields: Any,
) -> Mapping:
    """Build a `Mapping` whose subject and object both resolve in their ontology.

    The predicate is passed through unchecked. The mapping stores the CURIEs,
    not the expanded IRIs.

    Raises:
        ValidationError: If either CURIE is malformed or its prefix is unknown.
        UnresolvableCurieError: If either CURIE is absent from its graph.
    """
    resolve_curie(subject_curie, curie_map, subject_graph)
    resolve_curie(object_curie, curie_map, object_graph)
    return Mapping(
        subject_id=subject_curie,
        predicate_id=predicate,
        object_id=object_curie,
        mapping_justification=mapping_justification,
        **extra_fields,
    )
