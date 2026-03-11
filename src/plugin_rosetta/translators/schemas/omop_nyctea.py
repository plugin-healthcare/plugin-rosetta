"""Nyctea SchemaModels for OMOP CDM 5.4 Parquet output validation.

These models describe the expected column-level schema for the OMOP clinical
tables produced by the FHIR-to-OMOP translators.  They are used by
``plugin_rosetta.translators.io.omop_validator``.

Usage::

    from plugin_rosetta.translators.schemas.omop_nyctea import get_schema
    from plugin_rosetta.translators.io.omop_validator import validate_omop_dataframe

    result = validate_omop_dataframe(df, get_schema("person"))
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
# Person
# ---------------------------------------------------------------------------
PERSON_SCHEMA = SchemaModel(
    name="person",
    columns=[
        _col("person_id", "Int64", nullable=False, description="Primary key."),
        _col(
            "gender_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for gender.",
        ),
        _col("year_of_birth", "Int32", nullable=False, description="Year of birth."),
        _col("month_of_birth", "Int32", description="Month of birth (1-12)."),
        _col("day_of_birth", "Int32", description="Day of birth (1-31)."),
        _col("birth_datetime", "Utf8", description="Full birth datetime (ISO 8601)."),
        _col("gender_source_value", "Utf8", description="Source gender string."),
        _col(
            "gender_source_concept_id",
            "Int64",
            description="Source concept id for gender.",
        ),
        _col("race_concept_id", "Int64", description="Concept id for race."),
        _col("ethnicity_concept_id", "Int64", description="Concept id for ethnicity."),
    ],
)

# ---------------------------------------------------------------------------
# VisitOccurrence
# ---------------------------------------------------------------------------
VISIT_OCCURRENCE_SCHEMA = SchemaModel(
    name="visit_occurrence",
    columns=[
        _col(
            "visit_occurrence_id", "Int64", nullable=False, description="Primary key."
        ),
        _col("person_id", "Int64", nullable=False, description="FK to person."),
        _col(
            "visit_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for visit type.",
        ),
        _col(
            "visit_start_date",
            "Utf8",
            nullable=False,
            description="Visit start date (ISO date).",
        ),
        _col(
            "visit_start_datetime",
            "Utf8",
            description="Visit start datetime (ISO 8601).",
        ),
        _col("visit_end_date", "Utf8", description="Visit end date (ISO date)."),
        _col(
            "visit_end_datetime", "Utf8", description="Visit end datetime (ISO 8601)."
        ),
        _col(
            "visit_type_concept_id",
            "Int64",
            description="Concept id for visit type source.",
        ),
        _col("visit_source_value", "Utf8", description="Source value for visit type."),
        _col(
            "visit_source_concept_id",
            "Int64",
            description="Source concept id for visit type.",
        ),
        _col(
            "admitted_from_concept_id", "Int64", description="Admit source concept id."
        ),
        _col("admitted_from_source_value", "Utf8", description="Admit source value."),
        _col(
            "discharged_to_concept_id",
            "Int64",
            description="Discharge disposition concept id.",
        ),
        _col(
            "discharged_to_source_value",
            "Utf8",
            description="Discharge disposition source value.",
        ),
    ],
)

# ---------------------------------------------------------------------------
# ConditionOccurrence
# ---------------------------------------------------------------------------
CONDITION_OCCURRENCE_SCHEMA = SchemaModel(
    name="condition_occurrence",
    columns=[
        _col(
            "condition_occurrence_id",
            "Int64",
            nullable=False,
            description="Primary key.",
        ),
        _col("person_id", "Int64", nullable=False, description="FK to person."),
        _col(
            "condition_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for condition.",
        ),
        _col(
            "condition_start_date",
            "Utf8",
            nullable=False,
            description="Condition start date (ISO date).",
        ),
        _col(
            "condition_start_datetime",
            "Utf8",
            description="Condition start datetime (ISO 8601).",
        ),
        _col(
            "condition_end_date", "Utf8", description="Condition end date (ISO date)."
        ),
        _col(
            "condition_end_datetime",
            "Utf8",
            description="Condition end datetime (ISO 8601).",
        ),
        _col(
            "condition_type_concept_id",
            "Int64",
            description="Condition type concept id.",
        ),
        _col(
            "condition_status_concept_id",
            "Int64",
            description="Condition status concept id.",
        ),
        _col(
            "condition_source_value", "Utf8", description="Source value for condition."
        ),
        _col(
            "condition_source_concept_id",
            "Int64",
            description="Source concept id for condition.",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------
OBSERVATION_SCHEMA = SchemaModel(
    name="observation",
    columns=[
        _col("observation_id", "Int64", nullable=False, description="Primary key."),
        _col("person_id", "Int64", nullable=False, description="FK to person."),
        _col(
            "observation_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for observation.",
        ),
        _col(
            "observation_date",
            "Utf8",
            nullable=False,
            description="Observation date (ISO date).",
        ),
        _col(
            "observation_datetime",
            "Utf8",
            description="Observation datetime (ISO 8601).",
        ),
        _col(
            "observation_type_concept_id",
            "Int64",
            description="Observation type concept id.",
        ),
        _col("value_as_number", "Float64", description="Numeric value."),
        _col("value_as_string", "Utf8", description="String value."),
        _col("value_as_concept_id", "Int64", description="Coded value concept id."),
        _col("unit_concept_id", "Int64", description="Unit concept id."),
        _col(
            "observation_source_value",
            "Utf8",
            description="Source value for observation.",
        ),
        _col(
            "observation_source_concept_id", "Int64", description="Source concept id."
        ),
        _col(
            "value_source_value",
            "Utf8",
            description="Source value of the observation value.",
        ),
    ],
)

# ---------------------------------------------------------------------------
# ProcedureOccurrence
# ---------------------------------------------------------------------------
PROCEDURE_OCCURRENCE_SCHEMA = SchemaModel(
    name="procedure_occurrence",
    columns=[
        _col(
            "procedure_occurrence_id",
            "Int64",
            nullable=False,
            description="Primary key.",
        ),
        _col("person_id", "Int64", nullable=False, description="FK to person."),
        _col(
            "procedure_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for procedure.",
        ),
        _col(
            "procedure_date",
            "Utf8",
            nullable=False,
            description="Procedure date (ISO date).",
        ),
        _col(
            "procedure_datetime", "Utf8", description="Procedure datetime (ISO 8601)."
        ),
        _col(
            "procedure_end_date", "Utf8", description="Procedure end date (ISO date)."
        ),
        _col(
            "procedure_end_datetime",
            "Utf8",
            description="Procedure end datetime (ISO 8601).",
        ),
        _col(
            "procedure_type_concept_id",
            "Int64",
            description="Procedure type concept id.",
        ),
        _col(
            "procedure_source_value", "Utf8", description="Source value for procedure."
        ),
        _col(
            "procedure_source_concept_id",
            "Int64",
            description="Source concept id for procedure.",
        ),
    ],
)

# ---------------------------------------------------------------------------
# DrugExposure
# ---------------------------------------------------------------------------
DRUG_EXPOSURE_SCHEMA = SchemaModel(
    name="drug_exposure",
    columns=[
        _col("drug_exposure_id", "Int64", nullable=False, description="Primary key."),
        _col("person_id", "Int64", nullable=False, description="FK to person."),
        _col(
            "drug_concept_id",
            "Int64",
            nullable=False,
            description="Concept id for drug.",
        ),
        _col(
            "drug_exposure_start_date",
            "Utf8",
            nullable=False,
            description="Drug exposure start date.",
        ),
        _col(
            "drug_exposure_start_datetime",
            "Utf8",
            description="Drug exposure start datetime.",
        ),
        _col("drug_exposure_end_date", "Utf8", description="Drug exposure end date."),
        _col(
            "drug_exposure_end_datetime",
            "Utf8",
            description="Drug exposure end datetime.",
        ),
        _col("verbatim_end_date", "Utf8", description="Verbatim end date from source."),
        _col("drug_type_concept_id", "Int64", description="Drug type concept id."),
        _col("stop_reason", "Utf8", description="Reason drug was stopped."),
        _col(
            "quantity",
            "Float64",
            description="Quantity of drug dispensed/administered.",
        ),
        _col(
            "route_concept_id",
            "Int64",
            description="Route of administration concept id.",
        ),
        _col(
            "route_source_value",
            "Utf8",
            description="Route of administration source value.",
        ),
        _col("dose_unit_source_value", "Utf8", description="Dose unit source value."),
        _col("lot_number", "Utf8", description="Lot number (vaccines)."),
        _col("drug_source_value", "Utf8", description="Source value for drug."),
        _col(
            "drug_source_concept_id", "Int64", description="Source concept id for drug."
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
OMOP_SCHEMAS: dict[str, SchemaModel] = {
    "person": PERSON_SCHEMA,
    "visit_occurrence": VISIT_OCCURRENCE_SCHEMA,
    "condition_occurrence": CONDITION_OCCURRENCE_SCHEMA,
    "observation": OBSERVATION_SCHEMA,
    "procedure_occurrence": PROCEDURE_OCCURRENCE_SCHEMA,
    "drug_exposure": DRUG_EXPOSURE_SCHEMA,
}


def get_schema(table_name: str) -> SchemaModel:
    """Return the nyctea SchemaModel for a given OMOP table name.

    Args:
        table_name: Lowercase OMOP table name, e.g. ``"person"``,
            ``"visit_occurrence"``, ``"drug_exposure"``.

    Raises:
        KeyError: if no schema is registered for *table_name*.
    """
    try:
        return OMOP_SCHEMAS[table_name.lower()]
    except KeyError:
        raise KeyError(
            f"No OMOP nyctea schema registered for '{table_name}'. "
            f"Available: {sorted(OMOP_SCHEMAS)}"
        ) from None
