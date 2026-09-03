"""Schema conformance validation for authored mappings."""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.core.errors import ValidationError
from plugin_rosetta.mapping.models.sssom import Mapping

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping as MappingData


def validate_schema_conformance(rows: Iterable[MappingData[str, Any]]) -> tuple[Mapping, ...]:
    """Build generated SSSOM models from CSVW-typed rows."""
    mappings: list[Mapping] = []
    for index, row in enumerate(rows, start=2):
        try:
            mappings.append(Mapping.model_validate(row))
        except PydanticValidationError as error:
            raise ValidationError(f"SSSOM schema conformance failed at row {index}: {error}") from error
    return tuple(mappings)
