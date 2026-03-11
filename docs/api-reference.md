# API Reference

Full reference for the plugin-rosetta Python API. All public classes and functions
are documented here. Source code is shown inline.

---

## Base translator

The abstract base class all resource-specific translators extend.

::: plugin_rosetta.translators.base.FhirToOmopTranslator

---

## Translators

### PatientTranslator

::: plugin_rosetta.translators.fhir_to_omop.patient.PatientTranslator

---

### EncounterTranslator

::: plugin_rosetta.translators.fhir_to_omop.encounter.EncounterTranslator

---

### ConditionTranslator

::: plugin_rosetta.translators.fhir_to_omop.condition.ConditionTranslator

---

### ObservationTranslator

::: plugin_rosetta.translators.fhir_to_omop.observation.ObservationTranslator

---

### ProcedureTranslator

::: plugin_rosetta.translators.fhir_to_omop.procedure.ProcedureTranslator

---

### MedicationTranslator

::: plugin_rosetta.translators.fhir_to_omop.medication.MedicationTranslator

---

### ImmunizationTranslator

::: plugin_rosetta.translators.fhir_to_omop.immunization.ImmunizationTranslator

---

### AllergyTranslator

::: plugin_rosetta.translators.fhir_to_omop.allergy.AllergyTranslator

---

## I/O — NDJSON

::: plugin_rosetta.translators.io.ndjson_reader.iter_ndjson

::: plugin_rosetta.translators.io.ndjson_reader.read_ndjson

---

## I/O — Parquet

### Reading

::: plugin_rosetta.translators.io.parquet_reader.ParquetReadResult

::: plugin_rosetta.translators.io.parquet_reader.read_parquet

::: plugin_rosetta.translators.io.parquet_reader.read_parquet_validated

### Writing

::: plugin_rosetta.translators.io.parquet_writer.write_parquet

::: plugin_rosetta.translators.io.parquet_writer.rows_to_dataframe

---

## Validation

::: plugin_rosetta.translators.io.omop_validator.ValidationResult

::: plugin_rosetta.translators.io.omop_validator.validate_omop_parquet

::: plugin_rosetta.translators.io.omop_validator.validate_omop_dataframe

---

## Schema registry

OMOP and FHIR nyctea schema models used for columnar validation.

### OMOP schemas

```python
from plugin_rosetta.translators.schemas.omop_nyctea import get_schema

schema = get_schema("person")            # OMOP Person
schema = get_schema("visit_occurrence")  # OMOP VisitOccurrence
schema = get_schema("condition_occurrence")
schema = get_schema("observation")
schema = get_schema("procedure_occurrence")
schema = get_schema("drug_exposure")
```

### FHIR schemas

```python
from plugin_rosetta.translators.schemas.fhir_nyctea import get_schema

schema = get_schema("Patient")
schema = get_schema("Encounter")
schema = get_schema("Condition")
schema = get_schema("Observation")
schema = get_schema("Procedure")
schema = get_schema("MedicationStatement")
schema = get_schema("Immunization")
schema = get_schema("AllergyIntolerance")
```
