# plugin-rosetta

**plugin-rosetta** translates FHIR R4 clinical data into [OMOP CDM 5.4](https://ohdsi.github.io/CommonDataModel/) format. It uses [LinkML](https://linkml.io/) schemas to formally describe both models and to validate output — giving data engineers, clinical informaticians, and data stewards a transparent, auditable FHIR-to-OMOP pipeline.

Mappings are derived directly from the [HL7 FHIR-OMOP Implementation Guide](https://build.fhir.org/ig/HL7/fhir-omop-ig/) FML structure maps, ensuring alignment with the published standard rather than ad-hoc field-by-field decisions.

---

## Supported resources

| FHIR R4 resource | OMOP CDM 5.4 table |
|------------------|-------------------|
| Patient | Person |
| Encounter | VisitOccurrence |
| Condition | ConditionOccurrence |
| Observation (non-measurement) | Observation |
| Procedure | ProcedureOccurrence |
| MedicationStatement | DrugExposure |
| Immunization | DrugExposure |
| AllergyIntolerance | Observation |

---

## Where to go next

<div class="grid cards" markdown>

- **New to plugin-rosetta?**

    Install the library and translate your first FHIR record in minutes.

    [Getting Started](getting-started.md)

- **Auditing the mappings?**

    See exactly which FHIR fields map to which OMOP columns, with caveats.

    [Mappings](mappings.md)

- **Integrating the library?**

    Full API reference for translators, I/O helpers, and validators.

    [API Reference](api-reference.md)

- **Exploring the schemas?**

    Browse the generated LinkML schema documentation for all OMOP and FHIR classes.

    [Schema](elements/index.md)

</div>

---

## Known limitations

!!! warning "Concept IDs are not resolved"
    All `*_concept_id` fields in translator output are set to `0`. Mapping source
    codes (SNOMED, LOINC, RxNorm, etc.) to OMOP standard concepts requires a
    running OMOP vocabulary database or API — this is not yet implemented.
    The raw source code is always preserved in the corresponding `*_source_value`
    field.

!!! note "Measurement table not yet supported"
    FHIR Observations with `category` = `laboratory` or `vital-signs` are
    intentionally skipped. They belong in the OMOP `Measurement` table, which
    is planned for a future release.
