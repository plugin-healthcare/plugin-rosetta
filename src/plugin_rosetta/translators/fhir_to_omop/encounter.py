"""FHIR Encounter -> OMOP VisitOccurrence translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class EncounterTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Encounter resource to an OMOP VisitOccurrence row.

    Mapping source: EncounterVisit.fml (HL7 fhir-omop-ig 1.0.0-ballot).

    Notes:
    - ``visit_concept_id`` is populated from ``class.coding[0].code`` but
      requires a concept lookup to resolve to a standard OMOP concept.
      Until that lookup is implemented the source code is stored in
      ``visit_source_value`` and ``visit_concept_id`` is set to 0.
    - ``person_id`` and ``visit_occurrence_id`` are set to None; the caller
      must assign surrogate keys.
    """

    resource_type = "Encounter"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Visit type from class.coding[0].code
        visit_source_value: str | None = None
        for cls in record.get("class", []):
            code = self._first_coding_code(cls)
            if code:
                visit_source_value = code
                break

        # Period
        actual_period = record.get("actualPeriod", {}) or {}
        visit_start_datetime: str | None = actual_period.get("start")
        visit_end_datetime: str | None = actual_period.get("end")
        visit_start_date: str | None = (
            visit_start_datetime[:10] if visit_start_datetime else None
        )
        visit_end_date: str | None = (
            visit_end_datetime[:10] if visit_end_datetime else None
        )

        # Admission
        admission = record.get("admission", {}) or {}
        admitted_from_source_value: str | None = self._first_coding_code(
            admission.get("admitSource")
        )
        discharged_to_source_value: str | None = self._first_coding_code(
            admission.get("dischargeDisposition")
        )

        return {
            "visit_occurrence_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "visit_concept_id": 0,  # requires concept lookup
            "visit_start_date": visit_start_date,
            "visit_start_datetime": visit_start_datetime,
            "visit_end_date": visit_end_date,
            "visit_end_datetime": visit_end_datetime,
            "visit_type_concept_id": 0,
            "visit_source_value": visit_source_value,
            "visit_source_concept_id": 0,
            "admitted_from_concept_id": 0,
            "admitted_from_source_value": admitted_from_source_value,
            "discharged_to_concept_id": 0,
            "discharged_to_source_value": discharged_to_source_value,
        }
