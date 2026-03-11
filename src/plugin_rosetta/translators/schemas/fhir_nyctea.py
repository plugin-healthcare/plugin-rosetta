"""Nyctea SchemaModels for FHIR R4 Parquet input validation.

These models describe the expected column-level schema for FHIR resources
stored in tabular/Parquet form.  They are used by
``plugin_rosetta.translators.io.parquet_reader.read_parquet_validated``.

Only the columns that are directly mapped to OMOP are declared; extra
columns in the Parquet file are tolerated.

Usage::

    from plugin_rosetta.translators.schemas.fhir_nyctea import PATIENT_SCHEMA
    from plugin_rosetta.translators.io.parquet_reader import read_parquet_validated

    result = read_parquet_validated(path, PATIENT_SCHEMA)
    if not result.is_valid:
        print(result.errors)
"""

from __future__ import annotations

from nyctea.schema.model import ColumnSchema, SchemaModel  # type: ignore[import]


def _col(
    name: str,
    dtype: str,
    nullable: bool = True,
    description: str = "",
) -> ColumnSchema:
    return ColumnSchema(
        name=name,
        dtype=dtype,
        nullable=nullable,
        description=description,
    )


# ---------------------------------------------------------------------------
# Patient -> OMOP Person
# ---------------------------------------------------------------------------
PATIENT_SCHEMA = SchemaModel(
    name="Patient",
    columns=[
        _col("id", "Utf8", nullable=False, description="FHIR resource id"),
        _col("gender", "Utf8", description="Biological sex: male|female|other|unknown"),
        _col("birthDate", "Utf8", description="Date of birth (ISO 8601 date string)"),
    ],
)

# ---------------------------------------------------------------------------
# Encounter -> OMOP VisitOccurrence
# ---------------------------------------------------------------------------
ENCOUNTER_SCHEMA = SchemaModel(
    name="Encounter",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("class_code", "Utf8", description="Flattened class.coding[0].code"),
        _col(
            "actualPeriod_start",
            "Utf8",
            description="actualPeriod.start (ISO datetime)",
        ),
        _col("actualPeriod_end", "Utf8", description="actualPeriod.end (ISO datetime)"),
        _col(
            "admitSource_code",
            "Utf8",
            description="admission.admitSource.coding[0].code",
        ),
        _col(
            "dischargeDisposition_code",
            "Utf8",
            description="admission.dischargeDisposition.coding[0].code",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Condition -> OMOP ConditionOccurrence
# ---------------------------------------------------------------------------
CONDITION_SCHEMA = SchemaModel(
    name="Condition",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("code_code", "Utf8", description="code.coding[0].code"),
        _col(
            "recordedDate",
            "Utf8",
            description="Date condition first recorded (ISO date)",
        ),
        _col("onsetDateTime", "Utf8", description="Onset date/time (ISO datetime)"),
        _col(
            "abatementDateTime",
            "Utf8",
            description="Abatement date/time (ISO datetime)",
        ),
        _col("category_code", "Utf8", description="category[0].coding[0].code"),
        _col(
            "clinicalStatus_code", "Utf8", description="clinicalStatus.coding[0].code"
        ),
    ],
)

# ---------------------------------------------------------------------------
# Observation -> OMOP Observation
# ---------------------------------------------------------------------------
OBSERVATION_SCHEMA = SchemaModel(
    name="Observation",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("code_code", "Utf8", description="code.coding[0].code"),
        _col("category_code", "Utf8", description="category[0].coding[0].code"),
        _col(
            "effectiveDateTime",
            "Utf8",
            description="Effective date/time (ISO datetime)",
        ),
        _col(
            "valueQuantity_value", "Float64", description="value[x] as numeric quantity"
        ),
        _col("valueQuantity_unit", "Utf8", description="value[x] unit code"),
        _col(
            "valueCodeableConcept_code",
            "Utf8",
            description="value[x] as coded concept code",
        ),
        _col("valueString", "Utf8", description="value[x] as string"),
    ],
)

# ---------------------------------------------------------------------------
# Procedure -> OMOP ProcedureOccurrence
# ---------------------------------------------------------------------------
PROCEDURE_SCHEMA = SchemaModel(
    name="Procedure",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("code_code", "Utf8", description="code.coding[0].code"),
        _col(
            "occurrenceDateTime",
            "Utf8",
            description="Occurrence date/time (ISO datetime)",
        ),
        _col("occurrencePeriod_start", "Utf8", description="occurrencePeriod.start"),
        _col("occurrencePeriod_end", "Utf8", description="occurrencePeriod.end"),
    ],
)

# ---------------------------------------------------------------------------
# MedicationStatement -> OMOP DrugExposure
# ---------------------------------------------------------------------------
MEDICATION_STATEMENT_SCHEMA = SchemaModel(
    name="MedicationStatement",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col(
            "medication_code", "Utf8", description="medication.concept.coding[0].code"
        ),
        _col(
            "effectiveDateTime",
            "Utf8",
            description="Effective date/time (ISO datetime)",
        ),
        _col("effectivePeriod_start", "Utf8", description="effectivePeriod.start"),
        _col("effectivePeriod_end", "Utf8", description="effectivePeriod.end"),
        _col("category_code", "Utf8", description="category[0].coding[0].code"),
    ],
)

# ---------------------------------------------------------------------------
# Immunization -> OMOP DrugExposure
# ---------------------------------------------------------------------------
IMMUNIZATION_SCHEMA = SchemaModel(
    name="Immunization",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("vaccineCode_code", "Utf8", description="vaccineCode.coding[0].code"),
        _col(
            "occurrenceDateTime",
            "Utf8",
            description="Occurrence date/time (ISO datetime)",
        ),
        _col("doseQuantity_value", "Float64", description="doseQuantity.value"),
        _col("doseQuantity_code", "Utf8", description="doseQuantity.code"),
        _col("route_code", "Utf8", description="route.coding[0].code"),
        _col("lotNumber", "Utf8", description="Lot number"),
    ],
)

# ---------------------------------------------------------------------------
# AllergyIntolerance -> OMOP Observation
# ---------------------------------------------------------------------------
ALLERGY_SCHEMA = SchemaModel(
    name="AllergyIntolerance",
    columns=[
        _col("id", "Utf8", nullable=False),
        _col("code_code", "Utf8", description="code.coding[0].code"),
        _col("onsetDateTime", "Utf8", description="Onset date/time (ISO datetime)"),
        _col(
            "reaction_manifestation_code",
            "Utf8",
            description="reaction[0].manifestation[0].concept.coding[0].code",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
FHIR_SCHEMAS: dict[str, SchemaModel] = {
    "Patient": PATIENT_SCHEMA,
    "Encounter": ENCOUNTER_SCHEMA,
    "Condition": CONDITION_SCHEMA,
    "Observation": OBSERVATION_SCHEMA,
    "Procedure": PROCEDURE_SCHEMA,
    "MedicationStatement": MEDICATION_STATEMENT_SCHEMA,
    "Immunization": IMMUNIZATION_SCHEMA,
    "AllergyIntolerance": ALLERGY_SCHEMA,
}


def get_schema(resource_type: str) -> SchemaModel:
    """Return the nyctea SchemaModel for a given FHIR resource type.

    Raises:
        KeyError: if no schema is registered for *resource_type*.
    """
    try:
        return FHIR_SCHEMAS[resource_type]
    except KeyError:
        raise KeyError(
            f"No FHIR nyctea schema registered for '{resource_type}'. "
            f"Available: {sorted(FHIR_SCHEMAS)}"
        ) from None
