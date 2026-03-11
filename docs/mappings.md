# Mappings

This page documents how each FHIR R4 resource field maps to an OMOP CDM 5.4 column.
Mappings are derived from the [HL7 FHIR-OMOP Implementation Guide](https://build.fhir.org/ig/HL7/fhir-omop-ig/)
FML structure maps (tag `1.0.0-ballot`). The `exact_mappings` annotations in
`fhir_resources.yaml` are the machine-readable record of these mappings.

---

## How mappings work

The HL7 FHIR-OMOP IG publishes a set of [FHIR Mapping Language (FML)](https://hl7.org/fhir/mapping-language.html)
structure map files — one per resource — that formally specify the transformation
from FHIR to OMOP. plugin-rosetta parses these files at build time
(`parse_fml_mappings.py`) and injects `exact_mappings` into the corresponding
LinkML slot definitions in `fhir_resources.yaml`.

For example, the slot `Patient.gender` receives:

```yaml
exact_mappings:
  - omop:gender_concept_id
  - omop:gender_source_value
```

These annotations are the authoritative link between the two models — they drive
both the human-readable tables below and potential future code generation.

---

## General caveats

!!! warning "Concept IDs are always 0"
    All `*_concept_id` output fields are set to `0`. Resolving source codes
    (SNOMED CT, LOINC, RxNorm, CVX, etc.) to OMOP standard concept IDs requires
    a vocabulary lookup against an OMOP vocabulary database. This is not yet
    implemented. The raw source code is always preserved in the corresponding
    `*_source_value` field.

!!! note "Surrogate keys are not assigned"
    Primary key fields (`person_id`, `visit_occurrence_id`, etc.) and foreign key
    fields (`person_id` on clinical tables) are set to `None`. The calling ETL
    pipeline must assign these before loading into OMOP.

---

## Patient → Person

**FML source:** `PersonMap.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | Stored as a non-standard tracking field |
| `gender` | `gender_source_value` | Raw FHIR code (`male`, `female`, `other`, `unknown`) |
| `gender` | `gender_concept_id` | Always `0` — requires vocabulary lookup |
| `birthDate` (year) | `year_of_birth` | Parsed from ISO 8601 date string |
| `birthDate` (month) | `month_of_birth` | `None` if only year is present |
| `birthDate` (day) | `day_of_birth` | `None` if only year or year-month is present |
| `birthDate` | `birth_datetime` | Set to `YYYY-MM-DDT00:00:00` when full date is available |
| — | `race_concept_id` | Always `0` — FHIR R4 has no standard race element |
| — | `ethnicity_concept_id` | Always `0` — FHIR R4 has no standard ethnicity element |

---

## Encounter → VisitOccurrence

**FML source:** `EncounterVisit.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `class[].coding[0].code` | `visit_source_value` | First matching class code |
| `class[].coding[0].code` | `visit_concept_id` | Always `0` — requires vocabulary lookup |
| `actualPeriod.start` | `visit_start_datetime` | ISO 8601 datetime |
| `actualPeriod.start` (date part) | `visit_start_date` | First 10 characters |
| `actualPeriod.end` | `visit_end_datetime` | |
| `actualPeriod.end` (date part) | `visit_end_date` | |
| `admission.admitSource.coding[0].code` | `admitted_from_source_value` | |
| `admission.admitSource` | `admitted_from_concept_id` | Always `0` |
| `admission.dischargeDisposition.coding[0].code` | `discharged_to_source_value` | |
| `admission.dischargeDisposition` | `discharged_to_concept_id` | Always `0` |

---

## Condition → ConditionOccurrence

**FML source:** `condition.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `code.coding[0].code` | `condition_source_value` | |
| `code` | `condition_concept_id` | Always `0` — requires vocabulary lookup |
| `recordedDate` | `condition_start_date` | Preferred over `onsetDateTime` |
| `onsetDateTime` | `condition_start_datetime` | Used as start if `recordedDate` absent |
| `abatementDateTime` | `condition_end_date` | Date part only |
| `abatementDateTime` | `condition_end_datetime` | |
| `category[0].coding[0].code` | `condition_type_source_value` | |
| `clinicalStatus.coding[0].code` | `condition_status_source_value` | e.g. `active`, `resolved` |
| `evidence[0].concept[0].coding[0].code` | (evidence tracking field) | |

!!! note "Onset variants"
    Only `onsetDateTime` is handled. Other FHIR polymorphic onset types
    (`onsetPeriod`, `onsetAge`, `onsetRange`, `onsetString`) are not yet mapped.

---

## Observation → Observation

**FML source:** `Observation.fml`

!!! important "Routing by category"
    Only FHIR Observations with a `category` code in the following set are
    translated to the OMOP `Observation` table:

    `social-history`, `imaging`, `survey`, `exam`, `therapy`, `activity`, `procedure`

    Observations with `category` = `laboratory` or `vital-signs` are
    **intentionally skipped** (return an empty result). They are intended for a
    future `MeasurementTranslator` that maps to the OMOP `Measurement` table.

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `code.coding[0].code` | `observation_source_value` | Overridden by `note[0].text` if present |
| `code` | `observation_concept_id` | Always `0` |
| `effectiveDateTime` / `effectiveInstant` | `observation_datetime` | `effectivePeriod.start` used as fallback |
| `effectiveDateTime` (date part) | `observation_date` | |
| `valueQuantity.value` | `value_as_number` | |
| `valueQuantity.unit` / `.code` | `unit_source_value` | |
| `valueCodeableConcept.coding[0].code` | `value_source_value` | |
| `valueString` | `value_as_string` | |
| `note[0].text` | `observation_source_value` | Overrides code-derived value when present |

---

## Procedure → ProcedureOccurrence

**FML source:** `Procedure.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `code.coding[0].code` | `procedure_source_value` | |
| `code` | `procedure_concept_id` | Always `0` |
| `occurrenceDateTime` | `procedure_datetime` | Preferred over `occurrencePeriod` |
| `occurrenceDateTime` (date part) | `procedure_date` | |
| `occurrencePeriod.start` | `procedure_datetime` | Used when `occurrenceDateTime` is absent |
| `occurrencePeriod.end` | `procedure_end_datetime` | |

---

## MedicationStatement → DrugExposure

**FML source:** `medication.fml`

!!! note "MedicationStatement, not MedicationRequest"
    The HL7 FHIR-OMOP IG FML maps use `MedicationStatement`. If your source
    data uses `MedicationRequest`, the field paths differ and you will need a
    separate translator.

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `medication.concept.coding[0].code` | `drug_source_value` | |
| `medication` | `drug_concept_id` | Always `0` |
| `effectiveDateTime` | `drug_exposure_start_datetime` | Preferred over `effectivePeriod` |
| `effectiveDateTime` (date part) | `drug_exposure_start_date` | |
| `effectivePeriod.start` | `drug_exposure_start_datetime` | Used when `effectiveDateTime` absent |
| `effectivePeriod.end` | `drug_exposure_end_datetime` | |
| `category[0].coding[0].code` | `drug_type_source_value` | |
| `reason[0].concept.coding[0].code` | `stop_reason` | |

---

## Immunization → DrugExposure

**FML source:** `ImmunizationMap.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `vaccineCode.coding[0].code` | `drug_source_value` | |
| `vaccineCode` | `drug_concept_id` | Always `0` |
| `occurrenceDateTime` | `drug_exposure_start_datetime` | Also used as end datetime |
| `occurrenceDateTime` (date part) | `drug_exposure_start_date` | Also used as end date |
| `doseQuantity.value` | `quantity` | |
| `doseQuantity.code` / `.unit` | `dose_unit_source_value` | |
| `route.text` / `route.coding[0].code` | `route_source_value` | Text preferred over coding |
| `route` | `route_concept_id` | Always `0` |
| `lotNumber` | `lot_number` | |

---

## AllergyIntolerance → Observation

**FML source:** `Allergy.fml`

| FHIR field | OMOP column | Notes |
|-----------|------------|-------|
| `id` | `fhir_id` | |
| `code.coding[0].code` | `observation_source_value` | The allergy substance code |
| `code` | `observation_concept_id` | Always `0` |
| `onsetDateTime` | `observation_datetime` | |
| `onsetDateTime` (date part) | `observation_date` | |
| `reaction[0].manifestation[0].concept.coding[0].code` | `value_source_value` | First reaction manifestation code |
| `reaction[0].manifestation[0].concept` | `value_as_concept_id` | Always `0` |

---

## What is not mapped

| FHIR feature | Reason |
|-------------|--------|
| `Observation` with `laboratory` / `vital-signs` category | Belongs in OMOP `Measurement` — not yet implemented |
| `MedicationRequest` | The HL7 IG FML maps use `MedicationStatement`; `MedicationRequest` has different field paths |
| `DiagnosticReport`, `Specimen`, `Device`, etc. | Outside the scope of the 8 resources covered by the HL7 FHIR-OMOP IG FML maps |
| All `*_concept_id` fields | Vocabulary lookup against OMOP Athena is not yet implemented |
| `race_concept_id`, `ethnicity_concept_id` | FHIR R4 Patient has no standard race/ethnicity elements |
| `onsetPeriod`, `onsetAge`, `onsetRange`, `onsetString` | Only `onsetDateTime` is handled for Condition |
