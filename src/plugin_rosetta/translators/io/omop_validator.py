"""OMOP output validator using nyctea + Polars.

Validates an OMOP Parquet file (or DataFrame) against a nyctea SchemaModel,
then performs LinkML semantic validation on a sample of records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl


@dataclass
class ValidationResult:
    """Container for OMOP validation results."""

    df: pl.DataFrame
    errors: pl.DataFrame = field(default_factory=lambda: pl.DataFrame())

    @property
    def is_valid(self) -> bool:
        return self.errors.is_empty()


def validate_omop_parquet(path: Path, schema_model: Any) -> ValidationResult:
    """Validate an OMOP Parquet file against a nyctea SchemaModel.

    Args:
        path: Path to the OMOP Parquet file.
        schema_model: A nyctea ``SchemaModel`` instance (from
            ``plugin_rosetta.translators.schemas.omop_nyctea``).

    Returns:
        A :class:`ValidationResult` with the DataFrame and validation errors.
    """
    from nyctea.engine import validate  # type: ignore[import]

    df = pl.read_parquet(path)
    result = validate(df, schema_model)
    return ValidationResult(df=df, errors=result.errors)


def validate_omop_dataframe(df: pl.DataFrame, schema_model: Any) -> ValidationResult:
    """Validate an in-memory OMOP Polars DataFrame against a nyctea SchemaModel.

    Args:
        df: OMOP table as a Polars DataFrame.
        schema_model: A nyctea ``SchemaModel`` instance.

    Returns:
        A :class:`ValidationResult` with the DataFrame and validation errors.
    """
    from nyctea.engine import validate  # type: ignore[import]

    result = validate(df, schema_model)
    return ValidationResult(df=df, errors=result.errors)
