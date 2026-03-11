"""FHIR Procedure -> OMOP ProcedureOccurrence translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class ProcedureTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Procedure resource to an OMOP ProcedureOccurrence row.

    Mapping source: Procedure.fml (HL7 fhir-omop-ig 1.0.0-ballot).
    """

    resource_type = "Procedure"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Procedure code
        procedure_source_value: str | None = self._first_coding_code(record.get("code"))

        # Occurrence[x] - dateTime or Period
        procedure_datetime: str | None = record.get("occurrenceDateTime")
        procedure_end_datetime: str | None = None

        if procedure_datetime is None:
            period = record.get("occurrencePeriod", {}) or {}
            procedure_datetime = period.get("start")
            procedure_end_datetime = period.get("end")

        procedure_date: str | None = (
            procedure_datetime[:10] if procedure_datetime else None
        )
        procedure_end_date: str | None = (
            procedure_end_datetime[:10] if procedure_end_datetime else None
        )

        return {
            "procedure_occurrence_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "procedure_concept_id": 0,  # requires concept lookup
            "procedure_date": procedure_date,
            "procedure_datetime": procedure_datetime,
            "procedure_end_date": procedure_end_date,
            "procedure_end_datetime": procedure_end_datetime,
            "procedure_type_concept_id": 0,
            "procedure_source_value": procedure_source_value,
            "procedure_source_concept_id": 0,
        }
