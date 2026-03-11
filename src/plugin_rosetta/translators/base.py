"""Base class for FHIR-to-OMOP translators.

Each resource-specific translator (patient, encounter, etc.) should subclass
``FhirToOmopTranslator`` and implement ``translate_record``.

The three entry-points are:
  - ``translate_dict(record)``     – accepts a single FHIR resource as a dict
  - ``translate_ndjson(path)``     – reads FHIR ndjson line-by-line (orjson)
  - ``translate_parquet(path)``    – reads FHIR data from a Parquet file (Polars)

All translators return a list of dicts that can be assembled into OMOP tables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

import orjson
import polars as pl


class FhirToOmopTranslator(ABC):
    """Abstract base for per-resource FHIR-to-OMOP translators."""

    # Subclasses set this to the FHIR resourceType string they handle.
    resource_type: str = ""

    @abstractmethod
    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Translate one FHIR resource dict to one (flat) OMOP row dict.

        Returns an empty dict if the record cannot be translated.
        """
        ...

    # ------------------------------------------------------------------
    # Convenience entry-points
    # ------------------------------------------------------------------

    def translate_dict(self, record: dict[str, Any]) -> dict[str, Any]:
        """Translate a single FHIR resource dict."""
        return self.translate_record(record)

    def translate_ndjson(self, path: Path) -> list[dict[str, Any]]:
        """Read a FHIR ndjson file line-by-line and translate each record.

        Uses orjson for performance.  Lines that fail to parse or that have
        an unexpected resourceType are skipped with a warning.
        """
        results: list[dict[str, Any]] = []
        with open(path, "rb") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = orjson.loads(line)
                except orjson.JSONDecodeError as exc:
                    print(f"  Warning: line {lineno} JSON parse error: {exc}")
                    continue
                if (
                    self.resource_type
                    and record.get("resourceType") != self.resource_type
                ):
                    continue
                row = self.translate_record(record)
                if row:
                    results.append(row)
        return results

    def translate_parquet(self, path: Path) -> list[dict[str, Any]]:
        """Read a FHIR Parquet file with Polars and translate each record.

        Each Parquet row is converted to a plain Python dict and passed through
        ``translate_record``.  For complex nested schemas you may need to
        override this method.
        """
        df = pl.read_parquet(path)
        results: list[dict[str, Any]] = []
        for record in df.iter_rows(named=True):
            row = self.translate_record(record)
            if row:
                results.append(row)
        return results

    # ------------------------------------------------------------------
    # Helpers shared by subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def _get(record: dict[str, Any], *keys: str) -> Any:
        """Safely traverse a nested dict by key path.  Returns None if missing."""
        value: Any = record
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @staticmethod
    def _first_coding_code(codeable_concept: dict | None) -> str | None:
        """Return the first coding.code from a CodeableConcept dict."""
        if not isinstance(codeable_concept, dict):
            return None
        for coding in codeable_concept.get("coding", []):
            code = coding.get("code")
            if code is not None:
                return str(code)
        return None
