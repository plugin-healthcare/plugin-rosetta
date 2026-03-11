"""FHIR Patient -> OMOP Person translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class PatientTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 Patient resource to an OMOP Person row.

    Mapping source: PersonMap.fml (HL7 fhir-omop-ig 1.0.0-ballot).

    Notes:
    - ``person_id`` is taken from ``Patient.id`` (cast to int if numeric,
      else left as None — the ETL must assign a surrogate key).
    - Gender concept mapping (FHIR code -> OMOP concept_id) is not resolved
      here; ``gender_concept_id`` is set to 0 (unknown) and
      ``gender_source_value`` carries the raw FHIR code.
    - Race / ethnicity fields are not present in FHIR Patient R4 in a standard
      way and are therefore set to 0 (no matching concept).
    """

    resource_type = "Patient"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Birth date handling
        birth_date: str | None = record.get("birthDate")
        year_of_birth: int | None = None
        month_of_birth: int | None = None
        day_of_birth: int | None = None
        birth_datetime: str | None = None

        if birth_date:
            parts = birth_date.split("-")
            try:
                year_of_birth = int(parts[0]) if len(parts) >= 1 else None
                month_of_birth = int(parts[1]) if len(parts) >= 2 else None
                day_of_birth = int(parts[2]) if len(parts) >= 3 else None
                birth_datetime = (
                    birth_date + "T00:00:00" if len(parts) == 3 else birth_date
                )
            except (ValueError, IndexError):
                pass

        # Gender
        gender_source_value: str | None = record.get("gender")

        return {
            "person_id": None,  # surrogate key must be assigned by caller
            "fhir_id": fhir_id,
            "gender_concept_id": 0,  # requires concept lookup
            "year_of_birth": year_of_birth,
            "month_of_birth": month_of_birth,
            "day_of_birth": day_of_birth,
            "birth_datetime": birth_datetime,
            "race_concept_id": 0,
            "ethnicity_concept_id": 0,
            "gender_source_value": gender_source_value,
            "gender_source_concept_id": 0,
        }
