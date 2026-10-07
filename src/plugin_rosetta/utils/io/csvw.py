"""CSVW mapping input utilities."""

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from csvw import Table

from plugin_rosetta.errors import RosettaIOError, ValidationError
from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class MappingRows:
    """Typed CSVW rows and non-fatal input issues."""

    rows: tuple[dict[str, Any], ...]
    report: ValidationReport


def read_mapping_rows(csv_path: Path, metadata_path: Path) -> MappingRows:
    """Read mapping rows after checking CSVW conformance."""
    try:
        table = Table.from_file(metadata_path)
        if not isinstance(table, Table):
            raise ValidationError(f"CSVW metadata does not describe a table: {metadata_path}")
        rows = tuple(_as_row_dict(row) for row in table.iterdicts(fname=csv_path, strict=True))
    except (OSError, ValueError) as error:
        raise ValidationError(f"CSVW conformance failed for {csv_path}: {error}") from error

    primary_key = table.tableSchema.primaryKey if table.tableSchema else None
    if not primary_key:
        raise ValidationError(f"CSVW metadata is missing a primary key: {metadata_path}")
    _reject_duplicate_primary_keys(rows, tuple(primary_key))
    report = _empty_cell_report(csv_path)
    return MappingRows(rows=rows, report=report)


def _as_row_dict(row: dict[str, Any] | tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    return dict(row if isinstance(row, dict) else row[2])


def _reject_duplicate_primary_keys(rows: tuple[dict[str, Any], ...], primary_key: tuple[str, ...]) -> None:
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows, start=2):
        key = tuple(row[column] for column in primary_key)
        if key in seen:
            raise ValidationError(f"CSVW duplicate primary key at row {index}: {key}")
        seen.add(key)


def _empty_cell_report(csv_path: Path) -> ValidationReport:
    try:
        with csv_path.open(newline="") as stream:
            rows = tuple(csv.DictReader(stream))
    except OSError as error:
        raise RosettaIOError(f"Cannot inspect mapping CSV {csv_path}: {error}") from error

    issues = tuple(
        ValidationIssue(
            code="csvw.empty-cell",
            severity=IssueSeverity.WARNING,
            location=f"row {index}, column {column}",
            message="An explicit empty cell was parsed as an absent optional value.",
        )
        for index, row in enumerate(rows, start=2)
        for column, value in row.items()
        if value == ""
    )
    return ValidationReport(issues=issues)
