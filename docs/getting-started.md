# Getting Started

This guide walks you through installing plugin-rosetta and translating your first FHIR records into OMOP CDM format.

---

## Prerequisites

- Python >= 3.13
- `pip` or [`uv`](https://docs.astral.sh/uv/)

---

## Installation

Install plugin-rosetta from PyPI:

```bash
pip install plugin-rosetta
```


---

## Translating a single record

Each supported FHIR resource has its own translator class. All translators accept a plain Python `dict` via `translate_dict()` and return a flat OMOP row dict.

### Patient → Person

```python
from plugin_rosetta.translators.fhir_to_omop.patient import PatientTranslator

translator = PatientTranslator()

fhir_patient = {
    "resourceType": "Patient",
    "id": "pat-001",
    "gender": "female",
    "birthDate": "1985-03-22",
}

omop_person = translator.translate_dict(fhir_patient)
print(omop_person)
# {
#   "person_id": None,           # assign a surrogate key in your ETL
#   "fhir_id": "pat-001",
#   "gender_concept_id": 0,      # concept lookup not yet implemented
#   "year_of_birth": 1985,
#   "month_of_birth": 3,
#   "day_of_birth": 22,
#   "birth_datetime": "1985-03-22T00:00:00",
#   "race_concept_id": 0,
#   "ethnicity_concept_id": 0,
#   "gender_source_value": "female",
#   "gender_source_concept_id": 0,
# }
```

!!! warning "person_id is always None"
    Translators do not assign surrogate keys. Your ETL pipeline is responsible
    for populating `person_id` (and other `*_id` foreign keys) before loading
    into OMOP.

### Condition → ConditionOccurrence

```python
from plugin_rosetta.translators.fhir_to_omop.condition import ConditionTranslator

translator = ConditionTranslator()

fhir_condition = {
    "resourceType": "Condition",
    "id": "cond-001",
    "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
    "subject": {"reference": "Patient/pat-001"},
    "recordedDate": "2024-01-15",
    "clinicalStatus": {"coding": [{"code": "active"}]},
}

omop_condition = translator.translate_dict(fhir_condition)
# {
#   "condition_occurrence_id": None,
#   "fhir_id": "cond-001",
#   "condition_concept_id": 0,
#   "condition_start_date": "2024-01-15",
#   "condition_source_value": "44054006",
#   "condition_status_source_value": "active",
#   ...
# }
```

---

## Translating from NDJSON

Use `translate_ndjson()` to process a FHIR NDJSON file (one JSON resource per line). The translator automatically skips records with a non-matching `resourceType`.

```python
from pathlib import Path
from plugin_rosetta.translators.fhir_to_omop.encounter import EncounterTranslator

translator = EncounterTranslator()
rows = translator.translate_ndjson(Path("encounters.ndjson"))

# rows is a list of OMOP VisitOccurrence dicts
for row in rows:
    print(row["visit_source_value"], row["visit_start_date"])
```

---

## Translating from Parquet

Use `translate_parquet()` when your FHIR data is already in Parquet format (e.g. from a data lake). Each row is converted to a dict and passed through the translator.

```python
from pathlib import Path
from plugin_rosetta.translators.fhir_to_omop.procedure import ProcedureTranslator

translator = ProcedureTranslator()
rows = translator.translate_parquet(Path("procedures.parquet"))
```

---

## Writing OMOP output to Parquet

```python
from pathlib import Path
from plugin_rosetta.translators.fhir_to_omop.patient import PatientTranslator
from plugin_rosetta.translators.io.parquet_writer import write_parquet

translator = PatientTranslator()
rows = translator.translate_ndjson(Path("patients.ndjson"))

# Assign surrogate keys before writing
for i, row in enumerate(rows, start=1):
    row["person_id"] = i

write_parquet(rows, Path("output/person.parquet"))
```

---

## Validating OMOP output

### Python API

```python
from pathlib import Path
from plugin_rosetta.translators.io.omop_validator import validate_omop_parquet
from plugin_rosetta.translators.schemas.omop_nyctea import get_schema

result = validate_omop_parquet(Path("output/person.parquet"), get_schema("person"))

if result.errors:
    for error in result.errors:
        print(error)
else:
    print(f"Valid — {len(result.df)} rows")
```

### Command line

```bash
python -m plugin_rosetta.validate_omop output/person.parquet person
```

Available table names: `person`, `visit_occurrence`, `condition_occurrence`,
`observation`, `procedure_occurrence`, `drug_exposure`.

---

## All translator classes

| FHIR resource | Import path | OMOP table |
|--------------|------------|-----------|
| Patient | `plugin_rosetta.translators.fhir_to_omop.patient.PatientTranslator` | Person |
| Encounter | `plugin_rosetta.translators.fhir_to_omop.encounter.EncounterTranslator` | VisitOccurrence |
| Condition | `plugin_rosetta.translators.fhir_to_omop.condition.ConditionTranslator` | ConditionOccurrence |
| Observation | `plugin_rosetta.translators.fhir_to_omop.observation.ObservationTranslator` | Observation |
| Procedure | `plugin_rosetta.translators.fhir_to_omop.procedure.ProcedureTranslator` | ProcedureOccurrence |
| MedicationStatement | `plugin_rosetta.translators.fhir_to_omop.medication.MedicationTranslator` | DrugExposure |
| Immunization | `plugin_rosetta.translators.fhir_to_omop.immunization.ImmunizationTranslator` | DrugExposure |
| AllergyIntolerance | `plugin_rosetta.translators.fhir_to_omop.allergy.AllergyTranslator` | Observation |

---

## Development setup

If you are contributing to plugin-rosetta or need to regenerate the schemas:

```bash
# Prerequisites: Python >= 3.13, uv, just
uv tool install rust-just

uv sync --group dev

# Download OHDSI CSVs + HL7 FML mapping files
just download-sources

# Generate OMOP LinkML schemas and Pydantic models
just gen-omop-schema
just gen-pydantic

# Run the full test suite
uv run --no-sync python -m pytest

# Or regenerate everything in one step
just gen-all
```
