# plugin-rosetta

**plugin-rosetta** is a Python library that translates FHIR R4 clinical data into OMOP CDM 5.4 format using [LinkML](https://linkml.io/) schemas for validation and documentation.

It is part of the [plugin-healthcare](https://github.com/plugin-healthcare) ecosystem — a suite of composable data integration components for healthcare data engineering.

---

## Why plugin-rosetta?

Converting FHIR bundles to OMOP CDM is a recurring problem in clinical informatics. Most ETL pipelines are ad-hoc, hard to audit, and drift from both standards over time. plugin-rosetta addresses this by:

- **Grounding mappings in authoritative sources** — OMOP schemas are generated directly from [OHDSI CommonDataModel v5.4.2](https://github.com/OHDSI/CommonDataModel) CSVs; FHIR→OMOP field mappings are derived from the [HL7 FHIR-OMOP IG FML structure maps](https://github.com/HL7/fhir-omop-ig) (v1.0.0-ballot)
- **Machine-readable schemas** — both FHIR and OMOP models are expressed as [LinkML](https://linkml.io/) schemas, enabling validation, documentation generation, and downstream code generation
- **Flexible input formats** — accepts FHIR data as Python `dict`, NDJSON, or Parquet
- **Three-layer validation** — nyctea (columnar), Pydantic v2 (record-level), and LinkML semantic validation

---

## Supported resources

| FHIR R4 resource | OMOP CDM table |
|-----------------|---------------|
| Patient | Person |
| Encounter | VisitOccurrence |
| Condition | ConditionOccurrence |
| Observation (non-measurement) | Observation |
| Procedure | ProcedureOccurrence |
| MedicationStatement | DrugExposure |
| Immunization | DrugExposure |
| AllergyIntolerance | Observation |

> **Note:** FHIR Observations with `category` = `laboratory` or `vital-signs` are intentionally not translated here — they belong in the OMOP `Measurement` table, which is planned for a future release.

---

## Installation

```bash
pip install plugin-rosetta
```

**Additional step required:** [nyctea](https://github.com/yannick-vinkesteijn/nyctea) has an upstream packaging issue that prevents standard installation. Install it separately:

```bash
pip install --no-deps "nyctea @ git+https://github.com/yannick-vinkesteijn/nyctea.git@6b113f17c2d9fd578e56ca8c89555ac9a71f7130"
```

---

## Quick start

### Translate a single FHIR resource (dict)

```python
from plugin_rosetta.translators.fhir_to_omop.patient import PatientTranslator
from plugin_rosetta.translators.fhir_to_omop.condition import ConditionTranslator

translator = PatientTranslator()

fhir_patient = {
    "resourceType": "Patient",
    "id": "patient-001",
    "gender": "female",
    "birthDate": "1985-03-22",
}

omop_person = translator.translate_dict(fhir_patient)
# {
#   "person_id": None,        # assign surrogate key in your ETL
#   "fhir_id": "patient-001",
#   "gender_concept_id": 0,   # concept lookup not yet implemented
#   "year_of_birth": 1985,
#   "month_of_birth": 3,
#   "day_of_birth": 22,
#   "gender_source_value": "female",
#   ...
# }
```

### Translate from NDJSON

```python
from pathlib import Path
from plugin_rosetta.translators.fhir_to_omop.condition import ConditionTranslator

translator = ConditionTranslator()
rows = translator.translate_ndjson(Path("conditions.ndjson"))
# returns a list of OMOP ConditionOccurrence dicts
```

### Translate from Parquet

```python
from pathlib import Path
from plugin_rosetta.translators.fhir_to_omop.encounter import EncounterTranslator

translator = EncounterTranslator()
rows = translator.translate_parquet(Path("encounters.parquet"))
```

### Write OMOP output to Parquet

```python
from plugin_rosetta.translators.io.parquet_writer import write_parquet
from plugin_rosetta.translators.schemas.omop_nyctea import get_schema

write_parquet(rows, Path("person.parquet"), schema=get_schema("person"))
```

### Validate an existing OMOP Parquet file

```python
from plugin_rosetta.translators.io.omop_validator import validate_omop_parquet
from plugin_rosetta.translators.schemas.omop_nyctea import get_schema

result = validate_omop_parquet(Path("person.parquet"), get_schema("person"))
if result.errors:
    print(result.errors)
```

Or from the command line:

```bash
python -m plugin_rosetta.validate_omop person.parquet person
```

---

## Known limitations

- **Concept IDs are not resolved.** All `*_concept_id` fields in translator output are set to `0`. Mapping source codes to OMOP standard concepts requires a running OMOP vocabulary database (Athena) or API — this is not yet implemented.
- **`person_id` is not assigned.** Translators emit `person_id: None`; surrogate key assignment is the responsibility of the calling ETL pipeline.
- **No `Measurement` translator yet.** FHIR Observations with `laboratory` or `vital-signs` category are skipped.
- **`MedicationRequest` is not supported.** The HL7 FHIR-OMOP IG FML maps use `MedicationStatement`.

---

## Schema architecture

plugin-rosetta uses [LinkML](https://linkml.io/) to formally describe both data models. The schemas live under `src/plugin_rosetta/schema/`:

```
plugin_rosetta.yaml          ← root entry-point
├── omop_cdm.yaml            ← 27 OMOP CDM clinical tables (generated from OHDSI CSV)
├── omop_vocabulary.yaml     ← 10 OMOP vocabulary tables (generated)
├── omop_results.yaml        ← 2 OMOP results tables (generated)
└── fhir_resources.yaml      ← 8 FHIR R4 resources with exact_mappings (hand-authored)
```

Slots in `fhir_resources.yaml` carry `exact_mappings` to their OMOP counterparts (e.g. `omop:gender_concept_id`), derived from the HL7 FML structure maps. These mappings are the authoritative link between the two models.

---

## Development setup

```bash
# Prerequisites: Python >= 3.13, uv, just
uv tool install rust-just

# Install dependencies
uv sync --group dev

# Download upstream OMOP CSVs and HL7 FML files
just download-sources

# Generate OMOP LinkML schemas and Pydantic models
just gen-omop-schema
just gen-pydantic

# Run tests
uv run --no-sync python -m pytest

# Full pipeline in one step
just gen-all
```

See [AGENTS.md](AGENTS.md) for a complete guide to the repository, including architecture details, known bugs, and CI pipeline documentation.

---

## License

MIT
