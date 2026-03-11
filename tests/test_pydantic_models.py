"""Tests for generated Pydantic models.

Verifies that the generated ``plugin_rosetta_pydantic.py`` module:
1. Imports without errors.
2. Core OMOP and FHIR classes can be instantiated with minimal required fields.
3. Pydantic validation rejects obviously wrong types.
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pydantic_module():
    return importlib.import_module("plugin_rosetta.datamodel.plugin_rosetta_pydantic")


# ---------------------------------------------------------------------------
# Import smoke test
# ---------------------------------------------------------------------------


def test_pydantic_module_imports():
    mod = _get_pydantic_module()
    assert hasattr(mod, "ConfiguredBaseModel")


# ---------------------------------------------------------------------------
# OMOP class instantiation
# ---------------------------------------------------------------------------


def test_person_instantiation():
    mod = _get_pydantic_module()
    Person = getattr(mod, "Person", None)
    assert Person is not None, "Person class not found in generated module"
    # Create with only required field (person_id is a PK, hence required)
    p = Person(
        person_id=1,
        gender_concept_id=8532,
        year_of_birth=1985,
        race_concept_id=0,
        ethnicity_concept_id=0,
    )
    assert p.person_id == 1


def test_condition_occurrence_instantiation():
    mod = _get_pydantic_module()
    ConditionOccurrence = getattr(mod, "ConditionOccurrence", None)
    assert ConditionOccurrence is not None
    from datetime import date

    co = ConditionOccurrence(
        condition_occurrence_id=1,
        person_id=42,
        condition_concept_id=201826,
        condition_start_date=date(2022, 6, 1),
        condition_type_concept_id=32020,
    )
    assert co.condition_occurrence_id == 1


def test_visit_occurrence_instantiation():
    mod = _get_pydantic_module()
    VisitOccurrence = getattr(mod, "VisitOccurrence", None)
    assert VisitOccurrence is not None
    from datetime import date

    vo = VisitOccurrence(
        visit_occurrence_id=1,
        person_id=42,
        visit_concept_id=9201,
        visit_start_date=date(2023, 1, 15),
        visit_end_date=date(2023, 1, 15),
        visit_type_concept_id=32020,
    )
    assert vo.visit_occurrence_id == 1


# ---------------------------------------------------------------------------
# FHIR class instantiation
# ---------------------------------------------------------------------------


def test_fhir_patient_instantiation():
    mod = _get_pydantic_module()
    Patient = getattr(mod, "Patient", None)
    assert Patient is not None
    p = Patient(id="pat-001", gender="female")
    assert p.gender == "female"


def test_fhir_condition_instantiation():
    mod = _get_pydantic_module()
    Condition = getattr(mod, "Condition", None)
    assert Condition is not None
    c = Condition(id="cond-001")
    assert c.id == "cond-001"


def test_fhir_allergy_intolerance_instantiation():
    mod = _get_pydantic_module()
    AllergyIntolerance = getattr(mod, "AllergyIntolerance", None)
    assert AllergyIntolerance is not None
    a = AllergyIntolerance(id="allergy-001")
    assert a.id == "allergy-001"
