"""OMOP output Parquet writer.

Converts a list of OMOP row dicts to a Polars DataFrame and writes it
to a Parquet file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl


def write_parquet(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    schema: dict[str, pl.DataType] | None = None,
    compression: str = "zstd",
) -> pl.DataFrame:
    """Write OMOP row dicts to a Parquet file.

    Args:
        rows: List of dicts, each representing one OMOP table row.
        path: Destination Parquet file path.
        schema: Optional explicit Polars schema to enforce column dtypes.
            If None, Polars infers dtypes from the data.
        compression: Parquet compression codec.  Defaults to ``"zstd"``.

    Returns:
        The written Polars DataFrame.
    """
    if schema is not None:
        df = pl.DataFrame(rows, schema=schema)
    else:
        df = pl.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path, compression=compression)
    return df


def rows_to_dataframe(
    rows: list[dict[str, Any]],
    schema: dict[str, pl.DataType] | None = None,
) -> pl.DataFrame:
    """Convert OMOP row dicts to a Polars DataFrame without writing to disk."""
    if schema is not None:
        return pl.DataFrame(rows, schema=schema)
    return pl.DataFrame(rows)
