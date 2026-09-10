"""Declared contracts for tabular vocabulary release frames."""

from typing import TYPE_CHECKING, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.core.errors import ConfigurationError
from plugin_rosetta.core.report import IssueSeverity, ValidationIssue, ValidationReport
from plugin_rosetta.io.yaml import load_yaml_mapping

if TYPE_CHECKING:
    from pathlib import Path


class ColumnContract(BaseModel):
    """Required type and nullability for one release column."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dtype: Literal["String", "Int64", "Float64", "Boolean"]
    nullable: bool = True


class TableContract(BaseModel):
    """Tracked structural and content contract for a release table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    columns: dict[str, ColumnContract]


_POLARS_DTYPES = {
    "String": pl.String,
    "Int64": pl.Int64,
    "Float64": pl.Float64,
    "Boolean": pl.Boolean,
}


def load_table_contract(path: Path) -> TableContract:
    """Load a tracked vocabulary table contract."""
    raw_contract = load_yaml_mapping(path)
    try:
        return TableContract.model_validate(raw_contract)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid vocabulary table contract in {path}: {error}") from error


def validate_release_frame(
    frame: pl.DataFrame | pl.LazyFrame,
    contract: TableContract,
    *,
    source_path: Path,
) -> ValidationReport:
    """Validate a release frame behind the future Nyctea integration boundary."""
    lazy_frame = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    schema = lazy_frame.collect_schema()
    actual_columns = set(schema.names())
    expected_columns = set(contract.columns)
    issues: list[ValidationIssue] = []

    missing = sorted(expected_columns - actual_columns)
    if missing:
        issues.append(
            ValidationIssue(
                code="vocabulary.missing-columns",
                severity=IssueSeverity.ERROR,
                location=str(source_path),
                message=f"Missing expected columns: {', '.join(missing)}.",
            )
        )

    extra = sorted(actual_columns - expected_columns)
    if extra:
        issues.append(
            ValidationIssue(
                code="vocabulary.extra-columns",
                severity=IssueSeverity.INFO,
                location=str(source_path),
                message=f"Unexpected columns retained: {', '.join(extra)}.",
            )
        )

    required_columns: list[str] = []
    for name in sorted(expected_columns & actual_columns):
        column = contract.columns[name]
        expected_dtype = _POLARS_DTYPES[column.dtype]
        if schema[name] != expected_dtype:
            issues.append(
                ValidationIssue(
                    code="vocabulary.invalid-dtype",
                    severity=IssueSeverity.ERROR,
                    location=f"{source_path}:{name}",
                    message=f"Expected {column.dtype}, found {schema[name]}.",
                )
            )
        if not column.nullable:
            required_columns.append(name)

    if required_columns:
        null_counts = lazy_frame.select(pl.col(name).null_count().alias(name) for name in required_columns).collect()
        for name in required_columns:
            null_count = null_counts.item(0, name)
            if null_count:
                issues.append(
                    ValidationIssue(
                        code="vocabulary.null-value",
                        severity=IssueSeverity.ERROR,
                        location=f"{source_path}:{name}",
                        message=f"Required column {name!r} contains {null_count} null value(s).",
                    )
                )

    return ValidationReport(issues=tuple(issues))
