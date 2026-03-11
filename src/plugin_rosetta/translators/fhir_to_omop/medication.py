"""FHIR MedicationStatement -> OMOP DrugExposure translator.

Note: The fhir-omop-ig medication.fml maps MedicationStatement (not
MedicationRequest) to DrugExposure.  If your source data uses
MedicationRequest, adapt the ``resource_type`` and field paths accordingly.
"""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class MedicationTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 MedicationStatement to an OMOP DrugExposure row.

    Mapping source: medication.fml (HL7 fhir-omop-ig 1.0.0-ballot).
    """

    resource_type = "MedicationStatement"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Drug concept from medication.concept.coding[0].code
        medication = record.get("medication") or {}
        drug_source_value: str | None = None
        if isinstance(medication, dict):
            concept = medication.get("concept") or {}
            drug_source_value = self._first_coding_code(concept)

        # Effective[x]
        start_datetime: str | None = record.get("effectiveDateTime")
        end_datetime: str | None = None

        if start_datetime is None:
            period = record.get("effectivePeriod", {}) or {}
            start_datetime = period.get("start")
            end_datetime = period.get("end")

        start_date: str | None = start_datetime[:10] if start_datetime else None
        end_date: str | None = end_datetime[:10] if end_datetime else None

        # Drug type from category
        drug_type_source_value: str | None = None
        for cat in record.get("category", []):
            code = self._first_coding_code(cat)
            if code:
                drug_type_source_value = code
                break

        # Stop reason from reason
        stop_reason: str | None = None
        for reason in record.get("reason", []):
            if isinstance(reason, dict):
                concept = reason.get("concept") or {}
                code = self._first_coding_code(concept)
                if code:
                    stop_reason = code
                    break

        return {
            "drug_exposure_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "drug_concept_id": 0,  # requires concept lookup
            "drug_exposure_start_date": start_date,
            "drug_exposure_start_datetime": start_datetime,
            "drug_exposure_end_date": end_date,
            "drug_exposure_end_datetime": end_datetime,
            "verbatim_end_date": end_date,
            "drug_type_concept_id": 0,
            "stop_reason": stop_reason,
            "drug_source_value": drug_source_value,
            "drug_source_concept_id": 0,
            "drug_type_source_value": drug_type_source_value,
        }
