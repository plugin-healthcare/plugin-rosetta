"""Unit tests for FHIR-to-OMOP translator classes (dict input).

Each test exercises the ``translate_dict`` method with a minimal synthetic
FHIR resource and asserts the key OMOP output fields.
"""

from __future__ import annotations

import pytest

from plugin_rosetta.translators.fhir_to_omop.allergy import AllergyTranslator
from plugin_rosetta.translators.fhir_to_omop.condition import ConditionTranslator
from plugin_rosetta.translators.fhir_to_omop.encounter import EncounterTranslator
from plugin_rosetta.translators.fhir_to_omop.immunization import ImmunizationTranslator
from plugin_rosetta.translators.fhir_to_omop.medication import MedicationTranslator
from plugin_rosetta.translators.fhir_to_omop.observation import ObservationTranslator
from plugin_rosetta.translators.fhir_to_omop.patient import PatientTranslator
from plugin_rosetta.translators.fhir_to_omop.procedure import ProcedureTranslator


# ---------------------------------------------------------------------------
# Patient -> Person
# ---------------------------------------------------------------------------


class TestPatientTranslator:
    def setup_method(self):
        self.t = PatientTranslator()

    def test_basic_patient(self):
        fhir = {
            "resourceType": "Patient",
            "id": "pat-001",
            "gender": "female",
            "birthDate": "1985-03-22",
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "pat-001"
        assert row["gender_source_value"] == "female"
        assert row["year_of_birth"] == 1985
        assert row["month_of_birth"] == 3
        assert row["day_of_birth"] == 22
        assert row["birth_datetime"] == "1985-03-22T00:00:00"
        # Surrogate key not assigned yet
        assert row["person_id"] is None

    def test_partial_birth_date(self):
        fhir = {"resourceType": "Patient", "id": "pat-002", "birthDate": "1990-06"}
        row = self.t.translate_dict(fhir)
        assert row["year_of_birth"] == 1990
        assert row["month_of_birth"] == 6
        assert row["day_of_birth"] is None

    def test_missing_fields(self):
        row = self.t.translate_dict({"resourceType": "Patient", "id": "pat-003"})
        assert row["gender_source_value"] is None
        assert row["year_of_birth"] is None

    def test_resource_type_attribute(self):
        assert PatientTranslator.resource_type == "Patient"


# ---------------------------------------------------------------------------
# Encounter -> VisitOccurrence
# ---------------------------------------------------------------------------


class TestEncounterTranslator:
    def setup_method(self):
        self.t = EncounterTranslator()

    def test_basic_encounter(self):
        fhir = {
            "resourceType": "Encounter",
            "id": "enc-001",
            "class": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                            "code": "AMB",
                        }
                    ]
                }
            ],
            "actualPeriod": {
                "start": "2023-01-15T08:00:00",
                "end": "2023-01-15T09:30:00",
            },
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "enc-001"
        assert row["visit_source_value"] == "AMB"
        assert row["visit_start_date"] == "2023-01-15"
        assert row["visit_start_datetime"] == "2023-01-15T08:00:00"
        assert row["visit_end_date"] == "2023-01-15"
        assert row["visit_end_datetime"] == "2023-01-15T09:30:00"

    def test_admission_discharge(self):
        fhir = {
            "resourceType": "Encounter",
            "id": "enc-002",
            "admission": {
                "admitSource": {"coding": [{"code": "emd"}]},
                "dischargeDisposition": {"coding": [{"code": "home"}]},
            },
        }
        row = self.t.translate_dict(fhir)
        assert row["admitted_from_source_value"] == "emd"
        assert row["discharged_to_source_value"] == "home"

    def test_empty_encounter(self):
        row = self.t.translate_dict({"resourceType": "Encounter", "id": "enc-003"})
        assert row["visit_source_value"] is None
        assert row["visit_start_date"] is None


# ---------------------------------------------------------------------------
# Condition -> ConditionOccurrence
# ---------------------------------------------------------------------------


class TestConditionTranslator:
    def setup_method(self):
        self.t = ConditionTranslator()

    def test_basic_condition(self):
        fhir = {
            "resourceType": "Condition",
            "id": "cond-001",
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "44054006",
                        "display": "Diabetes mellitus type 2",
                    }
                ]
            },
            "recordedDate": "2022-06-01",
            "onsetDateTime": "2022-05-15T00:00:00",
            "abatementDateTime": "2023-01-01T00:00:00",
            "category": [{"coding": [{"code": "encounter-diagnosis"}]}],
            "clinicalStatus": {"coding": [{"code": "active"}]},
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "cond-001"
        assert row["condition_source_value"] == "44054006"
        assert row["condition_start_date"] == "2022-06-01"
        assert row["condition_start_datetime"] == "2022-05-15T00:00:00"
        assert row["condition_end_date"] == "2023-01-01"
        assert row["condition_end_datetime"] == "2023-01-01T00:00:00"
        assert row["condition_type_source_value"] == "encounter-diagnosis"
        assert row["condition_status_source_value"] == "active"

    def test_onset_only(self):
        fhir = {
            "resourceType": "Condition",
            "id": "cond-002",
            "onsetDateTime": "2021-11-10T00:00:00",
        }
        row = self.t.translate_dict(fhir)
        assert row["condition_start_date"] == "2021-11-10"
        assert row["condition_start_datetime"] == "2021-11-10T00:00:00"
        assert row["condition_end_date"] is None

    def test_no_code(self):
        row = self.t.translate_dict({"resourceType": "Condition", "id": "cond-003"})
        assert row["condition_source_value"] is None


# ---------------------------------------------------------------------------
# Observation -> Observation
# ---------------------------------------------------------------------------


class TestObservationTranslator:
    def setup_method(self):
        self.t = ObservationTranslator()

    def _obs_with_category(self, category_code: str, **extra) -> dict:
        """Helper: build an Observation with a known observation-category code."""
        return {
            "resourceType": "Observation",
            "id": "obs-001",
            "category": [{"coding": [{"code": category_code}]}],
            **extra,
        }

    def test_value_quantity(self):
        fhir = self._obs_with_category(
            "exam",
            code={"coding": [{"code": "8867-4", "system": "http://loinc.org"}]},
            effectiveDateTime="2023-03-10T10:00:00",
            valueQuantity={
                "value": 72.0,
                "unit": "bpm",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        )
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "obs-001"
        assert row["observation_source_value"] == "8867-4"
        assert row["observation_date"] == "2023-03-10"
        assert row["value_as_number"] == 72.0
        assert row["unit_source_value"] == "bpm"

    def test_value_codeable_concept(self):
        fhir = self._obs_with_category(
            "social-history",
            code={"coding": [{"code": "72166-2"}]},
            valueCodeableConcept={"coding": [{"code": "449868002"}]},
        )
        row = self.t.translate_dict(fhir)
        assert row["value_source_value"] == "449868002"

    def test_non_obs_category_returns_empty(self):
        """Observations with a laboratory/vital-signs category should be skipped."""
        fhir = {
            "resourceType": "Observation",
            "id": "obs-meas",
            "category": [{"coding": [{"code": "laboratory"}]}],
            "code": {"coding": [{"code": "2345-7"}]},
        }
        row = self.t.translate_dict(fhir)
        assert row == {}

    def test_no_category_returns_empty(self):
        row = self.t.translate_dict({"resourceType": "Observation", "id": "obs-x"})
        assert row == {}


# ---------------------------------------------------------------------------
# Procedure -> ProcedureOccurrence
# ---------------------------------------------------------------------------


class TestProcedureTranslator:
    def setup_method(self):
        self.t = ProcedureTranslator()

    def test_occurrence_datetime(self):
        fhir = {
            "resourceType": "Procedure",
            "id": "proc-001",
            "code": {"coding": [{"code": "80146002"}]},
            "occurrenceDateTime": "2023-04-20T14:00:00",
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "proc-001"
        assert row["procedure_source_value"] == "80146002"
        assert row["procedure_date"] == "2023-04-20"
        assert row["procedure_datetime"] == "2023-04-20T14:00:00"

    def test_occurrence_period(self):
        fhir = {
            "resourceType": "Procedure",
            "id": "proc-002",
            "occurrencePeriod": {
                "start": "2023-04-20T14:00:00",
                "end": "2023-04-20T15:30:00",
            },
        }
        row = self.t.translate_dict(fhir)
        assert row["procedure_date"] == "2023-04-20"
        assert row["procedure_end_date"] == "2023-04-20"


# ---------------------------------------------------------------------------
# MedicationStatement -> DrugExposure
# ---------------------------------------------------------------------------


class TestMedicationTranslator:
    def setup_method(self):
        self.t = MedicationTranslator()

    def test_effective_datetime(self):
        fhir = {
            "resourceType": "MedicationStatement",
            "id": "med-001",
            "medication": {"concept": {"coding": [{"code": "1049502"}]}},
            "effectiveDateTime": "2023-05-01T00:00:00",
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "med-001"
        assert row["drug_source_value"] == "1049502"
        assert row["drug_exposure_start_date"] == "2023-05-01"

    def test_effective_period(self):
        fhir = {
            "resourceType": "MedicationStatement",
            "id": "med-002",
            "effectivePeriod": {
                "start": "2023-05-01T00:00:00",
                "end": "2023-05-31T00:00:00",
            },
        }
        row = self.t.translate_dict(fhir)
        assert row["drug_exposure_start_date"] == "2023-05-01"
        assert row["drug_exposure_end_date"] == "2023-05-31"


# ---------------------------------------------------------------------------
# Immunization -> DrugExposure
# ---------------------------------------------------------------------------


class TestImmunizationTranslator:
    def setup_method(self):
        self.t = ImmunizationTranslator()

    def test_basic_immunization(self):
        fhir = {
            "resourceType": "Immunization",
            "id": "imm-001",
            "vaccineCode": {
                "coding": [{"code": "08", "system": "http://hl7.org/fhir/sid/cvx"}]
            },
            "occurrenceDateTime": "2022-09-15T00:00:00",
            "doseQuantity": {"value": 0.5, "unit": "mL", "code": "mL"},
            "route": {"coding": [{"code": "IM"}]},
            "lotNumber": "LOT-12345",
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "imm-001"
        assert row["drug_source_value"] == "08"
        assert row["drug_exposure_start_date"] == "2022-09-15"
        assert row["quantity"] == 0.5
        assert row["dose_unit_source_value"] == "mL"
        assert row["route_source_value"] == "IM"
        assert row["lot_number"] == "LOT-12345"


# ---------------------------------------------------------------------------
# AllergyIntolerance -> Observation
# ---------------------------------------------------------------------------


class TestAllergyTranslator:
    def setup_method(self):
        self.t = AllergyTranslator()

    def test_basic_allergy(self):
        fhir = {
            "resourceType": "AllergyIntolerance",
            "id": "allergy-001",
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": "372687004"}]
            },
            "onsetDateTime": "2010-03-15T00:00:00",
            "reaction": [
                {"manifestation": [{"concept": {"coding": [{"code": "271807003"}]}}]}
            ],
        }
        row = self.t.translate_dict(fhir)
        assert row["fhir_id"] == "allergy-001"
        assert row["observation_source_value"] == "372687004"
        assert row["observation_date"] == "2010-03-15"
        assert row["observation_datetime"] == "2010-03-15T00:00:00"
        assert row["value_source_value"] == "271807003"

    def test_no_reaction(self):
        fhir = {
            "resourceType": "AllergyIntolerance",
            "id": "allergy-002",
            "code": {"coding": [{"code": "123456"}]},
        }
        row = self.t.translate_dict(fhir)
        assert row["value_source_value"] is None
        assert row["observation_date"] is None

    def test_resource_type_attribute(self):
        assert AllergyTranslator.resource_type == "AllergyIntolerance"
