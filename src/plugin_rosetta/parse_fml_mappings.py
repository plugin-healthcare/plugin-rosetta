"""Parse FHIR-OMOP IG FML structure maps and enrich fhir_resources.yaml
with exact_mappings derived from the mapping rules.

Reads:
  sources/fhir-omop-ig/maps/*.fml

Writes:
  src/plugin_rosetta/schema/fhir_resources.yaml  (in-place enrichment)

The script extracts src->tgt field assignments from FML group rules using a
regex-based parser (FML is not a standard format with a Python library), then
merges any missing omop:* exact_mappings into the corresponding FHIR slot.

FHIR path -> LinkML slot name mapping is handled by a manual lookup table
because FML uses FHIR R4 path syntax (e.g. src.birthDate) while LinkML uses
camelCase slot names (e.g. birthDate).  The mapping is 1:1 for simple fields;
polymorphic choice types (e.g. onset:dateTime) are mapped to their concrete
slot names (e.g. onsetDateTime).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
FML_DIR = REPO_ROOT / "sources" / "fhir-omop-ig" / "maps"
FHIR_SCHEMA = REPO_ROOT / "src" / "plugin_rosetta" / "schema" / "fhir_resources.yaml"

OMOP_PREFIX = "omop:"

# ---------------------------------------------------------------------------
# FML source field -> FHIR LinkML slot name
# (only entries that differ from the plain field name need to be listed)
# ---------------------------------------------------------------------------
FML_SRC_TO_SLOT: dict[str, str] = {
    # Patient
    "gender": "gender",
    "birthDate": "birthDate",
    # Encounter
    "class": "class",
    "actualPeriod": "actualPeriod",
    "admission": "admission",
    "admitSource": "admitSource",
    "dischargeDisposition": "dischargeDisposition",
    # Condition (polymorphic)
    "onset:dateTime": "onsetDateTime",
    "abatement:dateTime": "abatementDateTime",
    "code": "code",
    "recordedDate": "recordedDate",
    "category": "category",
    "clinicalStatus": "clinicalStatus",
    "evidence": "evidence",
    # Observation (polymorphic)
    "effective:dateTime": "effectiveDateTime",
    "effective:instant": "effectiveDateTime",
    "effective:Period": "effectivePeriod",
    "issued": "issued",
    "value:Quantity": "valueQuantity",
    "value:CodeableConcept": "valueCodeableConcept",
    "value:string": "valueString",
    "note": "note",
    # Procedure (polymorphic)
    "occurrence:dateTime": "occurrenceDateTime",
    "occurrence:Period": "occurrencePeriod",
    # MedicationStatement (polymorphic)
    "medication:CodeableReference": "medication",
    "effective:dateTime": "effectiveDateTime",
    "effective:Period": "effectivePeriod",
    "reason:CodeableReference": "reason",
    # Immunization
    "vaccineCode": "vaccineCode",
    "occurrence:dateTime": "occurrenceDateTime",
    "doseQuantity": "doseQuantity",
    "route": "route",
    "lotNumber": "lotNumber",
    # AllergyIntolerance
    "onset:dateTime": "onsetDateTime",
    "reaction": "reaction",
}

# ---------------------------------------------------------------------------
# FML target field -> OMOP slot key
# (used to build omop:* exact_mapping values)
# ---------------------------------------------------------------------------
OMOP_TARGET_FIELDS: set[str] = {
    # Person
    "gender_concept_id",
    "gender_source_value",
    "birth_datetime",
    "year_of_birth",
    "month_of_birth",
    "day_of_birth",
    # VisitOccurrence
    "visit_concept_id",
    "visit_source_value",
    "visit_source_concept_id",
    "visit_start_date",
    "visit_start_datetime",
    "visit_end_date",
    "visit_end_datetime",
    "admitted_from_concept_id",
    "admitted_from_source_value",
    "discharged_to_concept_id",
    "discharged_to_source_value",
    # ConditionOccurrence
    "condition_concept_id",
    "condition_start_date",
    "condition_start_datetime",
    "condition_end_date",
    "condition_end_datetime",
    "condition_type_concept_id",
    "condition_status_concept_id",
    "condition_source_concept_id",
    # Observation
    "observation_concept_id",
    "observation_date",
    "observation_datetime",
    "observation_source_value",
    "observation_source_concept_id",
    "value_as_number",
    "unit_concept_id",
    "value_as_concept_id",
    "value_as_string",
    "value_source_value",
    # ProcedureOccurrence
    "procedure_concept_id",
    "procedure_source_value",
    "procedure_source_concept_id",
    "procedure_date",
    "procedure_datetime",
    "procedure_end_date",
    "procedure_end_datetime",
    # DrugExposure
    "drug_concept_id",
    "drug_source_value",
    "drug_source_concept_id",
    "drug_exposure_start_date",
    "drug_exposure_start_datetime",
    "drug_exposure_end_date",
    "drug_exposure_end_datetime",
    "verbatim_end_date",
    "drug_type_concept_id",
    "stop_reason",
    "quantity",
    "dose_unit_source_value",
    "route_concept_id",
    "route_source_value",
    "lot_number",
}

# ---------------------------------------------------------------------------
# Map FML file -> FHIR resource class name in fhir_resources.yaml
# ---------------------------------------------------------------------------
FML_FILE_TO_CLASS: dict[str, str] = {
    "PersonMap.fml": "Patient",
    "EncounterVisit.fml": "Encounter",
    "condition.fml": "Condition",
    "Observation.fml": "Observation",
    "Measurement.fml": "Observation",  # Measurement also targets Observation slots
    "Procedure.fml": "Procedure",
    "medication.fml": "MedicationStatement",
    "ImmunizationMap.fml": "Immunization",
    "Allergy.fml": "AllergyIntolerance",
}

# ---------------------------------------------------------------------------
# Regex patterns for FML parsing
# ---------------------------------------------------------------------------
# Matches lines like:  src.fieldName as x -> tgt.target_field = ...
# or:                  src.fieldName:Type as x -> tgt.target_field = ...
_SRC_FIELD_RE = re.compile(
    r"""src\.([\w]+(?::\s*[\w]+)?)   # src field (possibly :Type)
        \s+(?:as\s+\w+\s*->|->)      # 'as var ->' or '->'
    """,
    re.VERBOSE,
)

# Matches all target field names: tgt.some_field_name
_TGT_FIELD_RE = re.compile(r"tgt\.([\w]+)")


def parse_fml_mappings(fml_path: Path) -> dict[str, list[str]]:
    """Parse one FML file and return {src_field: [tgt_field, ...]}."""
    text = fml_path.read_text(encoding="utf-8")
    mappings: dict[str, list[str]] = defaultdict(list)

    for line in text.splitlines():
        line = line.strip()
        # Skip comments and group/uses declarations
        if line.startswith("//") or line.startswith("///") or not line:
            continue

        src_match = _SRC_FIELD_RE.search(line)
        if not src_match:
            continue

        src_field_raw = src_match.group(1).replace(" ", "")  # e.g. "onset:dateTime"
        tgt_fields = _TGT_FIELD_RE.findall(line)

        # Only keep tgt fields that are known OMOP columns
        omop_fields = [f for f in tgt_fields if f in OMOP_TARGET_FIELDS]
        if omop_fields:
            mappings[src_field_raw].extend(omop_fields)

    # Deduplicate while preserving order
    return {k: list(dict.fromkeys(v)) for k, v in mappings.items()}


def load_fhir_schema(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_fhir_schema(schema: dict, path: Path) -> None:
    # Use ruamel.yaml if available for round-trip preservation, else fallback to pyyaml
    try:
        from ruamel.yaml import YAML

        ry = YAML()
        ry.default_flow_style = False
        ry.width = 120
        ry.preserve_quotes = True
        with path.open("w", encoding="utf-8") as f:
            ry.dump(schema, f)
    except ImportError:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(
                schema,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )


def merge_exact_mappings(
    classes: dict,
    resource_class: str,
    src_field: str,
    omop_fields: list[str],
) -> int:
    """Add missing omop:* exact_mappings to the slot identified by src_field.

    Returns the number of new mappings added.
    """
    slot_name = FML_SRC_TO_SLOT.get(src_field)
    if not slot_name:
        return 0  # Unknown / not modelled

    cls = classes.get(resource_class)
    if not cls:
        return 0

    attributes = cls.get("attributes", {})
    slot = attributes.get(slot_name)
    if slot is None:
        return 0

    existing = set(slot.get("exact_mappings", []))
    added = 0
    for omop_field in omop_fields:
        mapping = f"{OMOP_PREFIX}{omop_field}"
        if mapping not in existing:
            if "exact_mappings" not in slot:
                slot["exact_mappings"] = []
            slot["exact_mappings"].append(mapping)
            existing.add(mapping)
            added += 1
    return added


def enrich_schema() -> None:
    schema = load_fhir_schema(FHIR_SCHEMA)
    classes = schema.get("classes", {})

    total_added = 0

    for fml_file, resource_class in FML_FILE_TO_CLASS.items():
        fml_path = FML_DIR / fml_file
        if not fml_path.exists():
            print(f"  Warning: FML file not found: {fml_path}")
            continue

        mappings = parse_fml_mappings(fml_path)
        file_added = 0

        for src_field, omop_fields in mappings.items():
            n = merge_exact_mappings(classes, resource_class, src_field, omop_fields)
            file_added += n

        if file_added:
            print(
                f"  {fml_file} -> {resource_class}: added {file_added} exact_mappings"
            )
        else:
            print(
                f"  {fml_file} -> {resource_class}: no new mappings (all already present)"
            )

        total_added += file_added

    save_fhir_schema(schema, FHIR_SCHEMA)
    print(f"\nTotal new exact_mappings added: {total_added}")
    print(f"Schema written: {FHIR_SCHEMA.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    print(
        "Enriching fhir_resources.yaml with exact_mappings from FML structure maps..."
    )
    enrich_schema()
    print("Done.")
