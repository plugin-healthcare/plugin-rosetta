"""FHIR Observation -> OMOP Observation translator.

Handles non-measurement Observation categories:
  social-history, imaging, survey, exam, therapy, activity, procedure.

Measurement-category Observations should use a separate MeasurementTranslator
(not yet implemented) that maps to the OMOP Measurement table instead.
"""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator

# FHIR categories that map to OMOP Observation (not Measurement)
OBS_CATEGORIES: frozenset[str] = frozenset(
    {"social-history", "imaging", "survey", "exam", "therapy", "activity", "procedure"}
)


class ObservationTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Observation to an OMOP Observation row.

    Mapping source: Observation.fml (HL7 fhir-omop-ig 1.0.0-ballot).

    Notes:
    - Records whose category codes are outside ``OBS_CATEGORIES`` are skipped
      (return empty dict).  Those should be routed to a MeasurementTranslator.
    - Polymorphic ``value[x]`` is handled for Quantity, CodeableConcept, string.
    """

    resource_type = "Observation"

    def _is_observation_category(self, record: dict[str, Any]) -> bool:
        for cat in record.get("category", []):
            for coding in cat.get("coding") or []:
                if coding.get("code") in OBS_CATEGORIES:
                    return True
        return False

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        # Route: only handle non-measurement observations
        if not self._is_observation_category(record):
            return {}

        fhir_id = record.get("id", "")

        # Observation code
        observation_source_value: str | None = self._first_coding_code(
            record.get("code")
        )

        # Effective date/time
        effective_datetime: str | None = record.get("effectiveDateTime") or record.get(
            "effectiveInstant"
        )
        if effective_datetime is None:
            period = record.get("effectivePeriod", {}) or {}
            effective_datetime = period.get("start")
        observation_date: str | None = (
            effective_datetime[:10] if effective_datetime else None
        )

        # Value[x]
        value_as_number: float | None = None
        unit_source_value: str | None = None
        value_as_concept_source: str | None = None
        value_as_string: str | None = None

        if "valueQuantity" in record:
            qty = record["valueQuantity"] or {}
            val = qty.get("value")
            value_as_number = float(val) if val is not None else None
            unit_source_value = qty.get("unit") or qty.get("code")
        elif "valueCodeableConcept" in record:
            value_as_concept_source = self._first_coding_code(
                record["valueCodeableConcept"]
            )
        elif "valueString" in record:
            value_as_string = str(record["valueString"])

        # Note -> observation_source_value override
        for note in record.get("note", []):
            text = note.get("text") if isinstance(note, dict) else str(note)
            if text:
                observation_source_value = text
                break

        return {
            "observation_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "observation_concept_id": 0,  # requires concept lookup
            "observation_date": observation_date,
            "observation_datetime": effective_datetime,
            "observation_type_concept_id": 0,
            "value_as_number": value_as_number,
            "value_as_string": value_as_string,
            "value_as_concept_id": 0,
            "unit_concept_id": 0,
            "observation_source_value": observation_source_value,
            "observation_source_concept_id": 0,
            "value_source_value": value_as_concept_source,
            "unit_source_value": unit_source_value,
        }
