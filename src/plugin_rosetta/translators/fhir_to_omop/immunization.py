"""FHIR Immunization -> OMOP DrugExposure translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class ImmunizationTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Immunization resource to an OMOP DrugExposure row.

    Mapping source: ImmunizationMap.fml (HL7 fhir-omop-ig 1.0.0-ballot).
    """

    resource_type = "Immunization"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Vaccine code
        drug_source_value: str | None = self._first_coding_code(
            record.get("vaccineCode")
        )

        # Occurrence datetime
        occurrence_datetime: str | None = record.get("occurrenceDateTime")
        occurrence_date: str | None = (
            occurrence_datetime[:10] if occurrence_datetime else None
        )

        # Dose quantity
        dose_qty = record.get("doseQuantity") or {}
        quantity: float | None = None
        dose_unit_source_value: str | None = None
        if isinstance(dose_qty, dict):
            val = dose_qty.get("value")
            quantity = float(val) if val is not None else None
            dose_unit_source_value = dose_qty.get("code") or dose_qty.get("unit")

        # Route
        route_source_value: str | None = None
        route = record.get("route") or {}
        if isinstance(route, dict):
            route_source_value = route.get("text") or self._first_coding_code(route)

        # Lot number
        lot_number: str | None = record.get("lotNumber")

        return {
            "drug_exposure_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "drug_concept_id": 0,  # requires concept lookup
            "drug_exposure_start_date": occurrence_date,
            "drug_exposure_start_datetime": occurrence_datetime,
            "drug_exposure_end_date": occurrence_date,
            "drug_exposure_end_datetime": occurrence_datetime,
            "drug_type_concept_id": 0,
            "quantity": quantity,
            "route_concept_id": 0,
            "route_source_value": route_source_value,
            "dose_unit_source_value": dose_unit_source_value,
            "lot_number": lot_number,
            "drug_source_value": drug_source_value,
            "drug_source_concept_id": 0,
        }
