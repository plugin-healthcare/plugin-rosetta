"""FHIR ndjson reader.

Reads a FHIR ndjson file and yields one dict per resource.
Uses orjson for performance.  Polars is deliberately NOT used here
because FHIR ndjson has heterogeneous schemas across resource types.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import orjson


def iter_ndjson(path: Path, resource_type: str | None = None) -> Iterator[dict]:
    """Yield dicts from a FHIR ndjson file, optionally filtered by resourceType.

    Args:
        path: Path to the ``.ndjson`` file.
        resource_type: If given, only yield records whose ``resourceType``
            matches this string.

    Yields:
        Parsed FHIR resource dicts.
    """
    with open(path, "rb") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record: dict = orjson.loads(line)
            except orjson.JSONDecodeError as exc:
                print(f"  Warning [{path.name}:{lineno}] JSON parse error: {exc}")
                continue
            if resource_type is None or record.get("resourceType") == resource_type:
                yield record


def read_ndjson(path: Path, resource_type: str | None = None) -> list[dict]:
    """Read all records from a FHIR ndjson file into a list.

    Convenience wrapper around :func:`iter_ndjson`.
    """
    return list(iter_ndjson(path, resource_type=resource_type))
