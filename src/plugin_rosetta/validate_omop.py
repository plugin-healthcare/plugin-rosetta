"""CLI script: validate an OMOP Parquet file against a nyctea schema.

Usage:
    python -m plugin_rosetta.validate_omop <path> <table_name>

Example:
    uv run python -m plugin_rosetta.validate_omop data/person.parquet person
"""

from __future__ import annotations

import sys
from pathlib import Path

from plugin_rosetta.translators.io.omop_validator import validate_omop_parquet
from plugin_rosetta.translators.schemas.omop_nyctea import get_schema


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <parquet_path> <table_name>", file=sys.stderr)
        sys.exit(2)

    parquet_path = Path(sys.argv[1])
    table_name = sys.argv[2]

    result = validate_omop_parquet(parquet_path, get_schema(table_name))

    if not result.errors.is_empty():
        print(result.errors)
        print(f"\n{len(result.errors)} validation errors found.", file=sys.stderr)
        sys.exit(1)

    print(f"Validation passed: {len(result.df)} rows in '{table_name}'.")


if __name__ == "__main__":
    main()
