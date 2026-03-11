"""FHIR Condition -> OMOP ConditionOccurrence translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class ConditionTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Condition resource to an OMOP ConditionOccurrence row.

    Mapping source: condition.fml (HL7 fhir-omop-ig 1.0.0-ballot).

    Notes:
    - ``condition_concept_id`` requires a terminology lookup from
      ``code.coding[0].code``; set to 0 until resolved.
    - Onset and abatement use the ``dateTime`` polymorphic variant only.
      Other onset types (Period, Age, Range, string) are not handled here.
    """

    resource_type = "Condition"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Condition code
        condition_source_value: str | None = self._first_coding_code(record.get("code"))

        # Start date: prefer recordedDate, fallback to onsetDateTime
        recorded_date: str | None = record.get("recordedDate")
        onset_datetime: str | None = record.get("onsetDateTime")
        start_raw = recorded_date or onset_datetime
        condition_start_date: str | None = start_raw[:10] if start_raw else None
        condition_start_datetime: str | None = onset_datetime or (
            recorded_date + "T00:00:00" if recorded_date else None
        )

        # End date
        abatement_datetime: str | None = record.get("abatementDateTime")
        condition_end_date: str | None = (
            abatement_datetime[:10] if abatement_datetime else None
        )

        # Type concept from category
        category_source_value: str | None = None
        for cat in record.get("category", []):
            code = self._first_coding_code(cat)
            if code:
                category_source_value = code
                break

        # Status
        status_source_value: str | None = self._first_coding_code(
            record.get("clinicalStatus")
        )

        # Source concept from evidence
        evidence_source_value: str | None = None
        for ev in record.get("evidence", []):
            for concept in ev.get("concept", []):
                code = self._first_coding_code(concept)
                if code:
                    evidence_source_value = code
                    break

        return {
            "condition_occurrence_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "condition_concept_id": 0,  # requires concept lookup
            "condition_start_date": condition_start_date,
            "condition_start_datetime": condition_start_datetime,
            "condition_end_date": condition_end_date,
            "condition_end_datetime": abatement_datetime,
            "condition_type_concept_id": 0,
            "condition_status_concept_id": 0,
            "condition_source_value": condition_source_value,
            "condition_source_concept_id": 0,
            "condition_status_source_value": status_source_value,
            "condition_type_source_value": category_source_value,
        }
