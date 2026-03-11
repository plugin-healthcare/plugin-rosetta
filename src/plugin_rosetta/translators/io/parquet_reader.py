"""FHIR / OMOP Parquet reader with nyctea validation.

Reads a Parquet file using Polars and optionally validates the schema
using a nyctea SchemaModel before returning the DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl


@dataclass
class ParquetReadResult:
    """Container for the result of reading a validated Parquet file."""

    df: pl.DataFrame
    errors: pl.DataFrame = field(default_factory=lambda: pl.DataFrame())

    @property
    def is_valid(self) -> bool:
        return self.errors.is_empty()


def read_parquet(path: Path) -> pl.DataFrame:
    """Read a Parquet file and return a Polars DataFrame.

    No validation is applied; use :func:`read_parquet_validated` if you need
    schema validation via nyctea.
    """
    return pl.read_parquet(path)


def read_parquet_validated(path: Path, schema_model) -> ParquetReadResult:
    """Read a Parquet file and validate it against a nyctea SchemaModel.

    Args:
        path: Path to the Parquet file.
        schema_model: A nyctea ``SchemaModel`` instance describing the expected
            column schema.

    Returns:
        A :class:`ParquetReadResult` containing the DataFrame and any
        validation errors as a Polars DataFrame.
    """
    from nyctea.engine import validate  # type: ignore[import]

    df = pl.read_parquet(path)
    result = validate(df, schema_model)
    return ParquetReadResult(df=df, errors=result.errors)
