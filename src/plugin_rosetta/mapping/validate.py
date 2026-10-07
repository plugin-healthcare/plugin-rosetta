"""Validation of authored mappings: schema conformance and referential integrity.

Schema conformance only proves a row is well formed. Referential integrity
re-checks every `subject_id`/`object_id` against the ontology graph it should
belong to, which is what catches a term that was valid when authored but has
since been removed or renamed upstream.
"""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.mapping.curies import expand_curie
from plugin_rosetta.mapping.models.sssom import Mapping
from plugin_rosetta.ontology.catalog import resource_exists
from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping as MappingData

    from rdflib import Graph

    from plugin_rosetta.mapping.models.sssom import MappingSet

# The authored CSV's header occupies row 1, so mappings are numbered from row 2
# and every reported row number points at the line the curator has to edit.
FIRST_MAPPING_ROW = 2


def validate_schema_conformance(rows: Iterable[MappingData[str, Any]]) -> tuple[Mapping, ...]:
    """Build generated SSSOM models from CSVW-typed rows."""
    mappings: list[Mapping] = []
    for index, row in enumerate(rows, start=FIRST_MAPPING_ROW):
        try:
            mappings.append(Mapping.model_validate(row))
        except PydanticValidationError as error:
            raise ValidationError(f"SSSOM schema conformance failed at row {index}: {error}") from error
    return tuple(mappings)


def _check_identifier(
    row: int,
    field: str,
    curie: str | None,
    curie_map: MappingData[str, str],
    graph: Graph,
) -> ValidationIssue | None:
    location = f"row {row}, column {field}"
    if curie is None:
        return ValidationIssue(
            code="referential.missing-field",
            severity=IssueSeverity.ERROR,
            location=location,
            message=f"Row {row} has no {field}.",
        )
    try:
        iri = expand_curie(curie, curie_map)
    except ValidationError as error:
        return ValidationIssue(
            code="referential.unknown-prefix",
            severity=IssueSeverity.ERROR,
            location=location,
            message=f"Row {row} {field} {curie!r} cannot be expanded: {error}",
        )
    if not resource_exists(graph, iri):
        return ValidationIssue(
            code="referential.unresolved",
            severity=IssueSeverity.ERROR,
            location=location,
            message=f"Row {row} {field} {curie!r} (expands to {iri!r}) was not found in the ontology graph.",
        )
    return None


def validate_referential_integrity(
    mapping_set: MappingSet,
    *,
    curie_map: MappingData[str, str],
    subject_graph: Graph,
    object_graph: Graph,
) -> ValidationReport:
    """Check every mapping's subject and object against its ontology graph.

    Predicates and other CURIE-valued fields are passed through: the mapping
    set's `curie_map` also carries prefixes such as `skos`, `semapv`, and
    `orcid`, which name no ontology term to resolve.
    """
    issues = [
        issue
        for row, mapping in enumerate(mapping_set.mappings or [], start=FIRST_MAPPING_ROW)
        for field, curie, graph in (
            ("subject_id", mapping.subject_id, subject_graph),
            ("object_id", mapping.object_id, object_graph),
        )
        if (issue := _check_identifier(row, field, curie, curie_map, graph)) is not None
    ]
    return ValidationReport(issues=tuple(issues))
