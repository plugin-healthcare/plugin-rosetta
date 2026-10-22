"""Deterministic SSSOM/TSV input and output utilities."""

import csv
import io
import types
from pathlib import Path
from typing import Any, Union, get_args, get_origin

import yaml
from linkml_runtime.utils.metamodelcore import URI
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import RosettaIOError, ValidationError
from plugin_rosetta.mapping.models.sssom import Mapping, MappingSet
from plugin_rosetta.utils.io.atomic import atomic_write_text

_KEY_FIELDS = ("subject_id", "predicate_id", "object_id", "mapping_justification")


def write_sssom_tsv(mapping_set: MappingSet, destination: Path) -> None:
    """Write a mapping set as deterministic embedded-metadata SSSOM/TSV."""
    atomic_write_text(destination, render_sssom_tsv(mapping_set))


def render_sssom_tsv(mapping_set: MappingSet) -> str:
    """Render deterministic embedded-metadata SSSOM/TSV without writing it."""
    mappings = _require_mappings(mapping_set)
    columns = _populated_columns(mappings)
    output = io.StringIO(newline="")
    metadata = {
        "mapping_set_id": str(mapping_set.mapping_set_id),
        "license": str(mapping_set.license),
        "curie_map": mapping_set.curie_map or {},
    }
    for line in yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).splitlines():
        output.write(f"# {line}\n")
    writer = csv.DictWriter(output, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for mapping in mappings:
        writer.writerow({column: _format_cell(getattr(mapping, column)) for column in columns})
    return output.getvalue()


def read_sssom_tsv(source: Path) -> MappingSet:
    """Read an embedded-metadata SSSOM/TSV file.

    Raises:
        RosettaIOError: If the file cannot be read.
    """
    try:
        lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError as error:
        raise RosettaIOError(f"Cannot read SSSOM file {source}: {error}") from error

    table_start = next((index for index, line in enumerate(lines) if not line.startswith("#")), None)
    if table_start is None:
        raise ValidationError(f"SSSOM file has no table: {source}")
    metadata_lines = [line.removeprefix("#").removeprefix(" ").rstrip("\r\n") for line in lines[:table_start]]

    metadata = yaml.safe_load("\n".join(metadata_lines))
    if not isinstance(metadata, dict):
        raise ValidationError(f"SSSOM metadata is not a mapping: {source}")
    reader = csv.DictReader(io.StringIO("".join(lines[table_start:]), newline=""), delimiter="\t")
    unknown = [field for field in reader.fieldnames or [] if field not in Mapping.model_fields]
    if unknown:
        raise ValidationError(f"Unknown SSSOM column(s) in {source}: {', '.join(unknown)}")
    mappings: list[Mapping] = []
    for index, row in enumerate(reader, start=2):
        values = {field: _parse_cell(field, value) for field, value in row.items()}
        try:
            mappings.append(Mapping.model_validate(values))
        except PydanticValidationError as error:
            raise ValidationError(f"Invalid SSSOM mapping at row {index}: {error}") from error
    try:
        return MappingSet(
            mapping_set_id=URI(metadata["mapping_set_id"]),
            license=URI(metadata["license"]),
            curie_map=metadata.get("curie_map", {}),
            mappings=mappings,
        )
    except (KeyError, PydanticValidationError) as error:
        raise ValidationError(f"Invalid SSSOM metadata in {source}: {error}") from error


def _require_mappings(mapping_set: MappingSet) -> list[Mapping]:
    mappings = mapping_set.mappings or []
    for index, mapping in enumerate(mappings, start=1):
        for field in _KEY_FIELDS:
            if not getattr(mapping, field):
                raise ValidationError(f"Mapping {index} has no {field}")
    return mappings


def _populated_columns(mappings: list[Mapping]) -> tuple[str, ...]:
    model_order = tuple(Mapping.model_fields)
    ordered = _KEY_FIELDS + tuple(field for field in model_order if field not in _KEY_FIELDS)
    return tuple(
        field
        for field in ordered
        if field in _KEY_FIELDS or any(_has_value(getattr(mapping, field)) for mapping in mappings)
    )


def _has_value(value: object) -> bool:
    return value not in (None, [], "")


def _format_cell(value: object) -> object:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if value is None:
        return ""
    return value


def _parse_cell(field: str, value: str | None) -> object:
    if _is_list_field(field):
        return [] if not value else value.split("|")
    return None if value in (None, "") else value


def _is_list_field(field: str) -> bool:
    return _contains_list(Mapping.model_fields[field].annotation)


def _contains_list(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is list:
        return True
    # Before 3.14, Optional[...] has origin typing.Union, distinct from types.UnionType.
    if origin in {Union, types.UnionType}:
        return any(_contains_list(member) for member in get_args(annotation))
    return False
