"""FHIR AllergyIntolerance -> OMOP Observation translator."""

from __future__ import annotations

from typing import Any

from plugin_rosetta.translators.base import FhirToOmopTranslator


class AllergyTranslator(FhirToOmopTranslator):
    """Translate a FHIR R4 AllergyIntolerance resource to an OMOP Observation row.

    Mapping source: Allergy.fml (HL7 fhir-omop-ig 1.0.0-ballot).
    """

    resource_type = "AllergyIntolerance"

    def translate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fhir_id = record.get("id", "")

        # Allergy code -> observation_concept_id / observation_source_value
        observation_source_value: str | None = self._first_coding_code(
            record.get("code")
        )

        # Onset datetime
        onset_datetime: str | None = record.get("onsetDateTime")
        observation_date: str | None = onset_datetime[:10] if onset_datetime else None

        # Reaction manifestation -> value_as_concept_id / value_source_value
        value_source_value: str | None = None
        for reaction in record.get("reaction", []):
            if not isinstance(reaction, dict):
                continue
            for manifestation in reaction.get("manifestation", []):
                if not isinstance(manifestation, dict):
                    continue
                concept = manifestation.get("concept") or {}
                code = self._first_coding_code(concept)
                if code:
                    value_source_value = code
                    break
            if value_source_value:
                break

        return {
            "observation_id": None,
            "fhir_id": fhir_id,
            "person_id": None,
            "observation_concept_id": 0,  # requires concept lookup
            "observation_date": observation_date,
            "observation_datetime": onset_datetime,
            "observation_type_concept_id": 0,
            "value_as_concept_id": 0,
            "observation_source_value": observation_source_value,
            "observation_source_concept_id": 0,
            "value_source_value": value_source_value,
        }
