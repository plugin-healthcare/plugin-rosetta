"""Generate LinkML YAML schemas from OHDSI OMOP CDM v5.4 CSV source files.

Reads:
  sources/omop/OMOP_CDMv5.4_Field_Level.csv
  sources/omop/OMOP_CDMv5.4_Table_Level.csv

Writes (into src/plugin_rosetta/schema/):
  omop_cdm.yaml       - CDM clinical tables
  omop_vocabulary.yaml - VOCAB reference tables
  omop_results.yaml   - RESULTS (cohort) tables
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO_ROOT / "sources" / "omop"
SCHEMA_DIR = REPO_ROOT / "src" / "plugin_rosetta" / "schema"

FIELD_LEVEL_CSV = SOURCES_DIR / "OMOP_CDMv5.4_Field_Level.csv"
TABLE_LEVEL_CSV = SOURCES_DIR / "OMOP_CDMv5.4_Table_Level.csv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEMA_BASE_URI = "https://w3id.org/plugin-rosetta/"
OMOP_CDM_VERSION = "5.4.2"

# OMOP datatype -> LinkML range
DATATYPE_MAP: dict[str, str] = {
    "integer": "integer",
    "Integer": "integer",
    "float": "float",
    "date": "date",
    "datetime": "datetime",
    "varchar(max)": "string",
    "varchar(MAX)": "string",
}


# Any varchar(N) -> string
def _linkml_range(cdm_datatype: str) -> str:
    dt = cdm_datatype.strip()
    if dt in DATATYPE_MAP:
        return DATATYPE_MAP[dt]
    if re.match(r"varchar\(\d+\)", dt, re.IGNORECASE):
        return "string"
    return "string"  # safe fallback


def _to_class_name(table_name: str) -> str:
    """Convert OMOP table name to PascalCase LinkML class name."""
    return "".join(word.capitalize() for word in table_name.lower().split("_"))


def _yaml_str(value: str) -> str:
    """Wrap a string value safely for YAML using double-quoted scalars."""
    value = value.strip()
    if not value or value == "NA":
        return '""'
    # Normalize whitespace: collapse newlines/runs of spaces into single spaces
    value = " ".join(value.split())
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# Read source CSVs
# ---------------------------------------------------------------------------
def read_table_level() -> dict[str, dict]:
    """Return {table_name_lower: row_dict} from the table-level CSV."""
    tables = {}
    with open(TABLE_LEVEL_CSV, newline="", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            name = row["cdmTableName"].strip().lower()
            tables[name] = row
    return tables


def read_field_level() -> dict[str, list[dict]]:
    """Return {table_name_lower: [field_row, ...]} preserving column order."""
    fields: dict[str, list[dict]] = defaultdict(list)
    with open(FIELD_LEVEL_CSV, newline="", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            table = row["cdmTableName"].strip().lower()
            fields[table].append(row)
    return fields


# ---------------------------------------------------------------------------
# Schema generation helpers
# ---------------------------------------------------------------------------
def _render_slot(field: dict, class_name: str) -> str:
    """Render a single LinkML slot (attribute) block for a field row."""
    slot_name = field["cdmFieldName"].strip().lower().strip('"')
    is_required = field["isRequired"].strip().lower() == "yes"
    is_pk = field["isPrimaryKey"].strip().lower() == "yes"
    is_fk = field["isForeignKey"].strip().lower() == "yes"
    fk_table = field["fkTableName"].strip()
    cdm_datatype = field["cdmDatatype"].strip()
    user_guidance = field["userGuidance"].strip()
    etl_conventions = field["etlConventions"].strip()
    fk_domain = field["fkDomain"].strip()

    lines = [f"      {slot_name}:"]

    # Range: FK -> class reference, otherwise scalar
    if is_fk and fk_table and fk_table.upper() not in ("NA", ""):
        fk_class = _to_class_name(fk_table)
        lines.append(f"        range: {fk_class}")
        if fk_domain and fk_domain not in ("NA", ""):
            lines.append(f"        # fk_domain: {fk_domain}")
    else:
        lines.append(f"        range: {_linkml_range(cdm_datatype)}")

    if is_pk:
        lines.append("        identifier: true")
        lines.append("        required: true")
    elif is_required:
        lines.append("        required: true")
    else:
        lines.append("        required: false")

    # slot_uri: use Athena OMOP prefix
    lines.append(f"        slot_uri: omop:{slot_name}")

    # Description from userGuidance
    if user_guidance and user_guidance.upper() not in ("NA", ""):
        desc_value = _yaml_str(user_guidance)
        lines.append(f"        description: {desc_value}")

    # ETL conventions as a comment / notes field
    if etl_conventions and etl_conventions.upper() not in ("NA", ""):
        comment_value = _yaml_str(etl_conventions)
        lines.append(f"        comments:")
        lines.append(f"          - {comment_value}")

    return "\n".join(lines)


def _render_class(table_name: str, table_meta: dict, fields: list[dict]) -> str:
    """Render a full LinkML class block for one OMOP table."""
    class_name = _to_class_name(table_name)
    table_desc = table_meta.get("tableDescription", "").strip()
    user_guidance = table_meta.get("userGuidance", "").strip()
    schema_group = table_meta.get("schema", "CDM").strip()
    is_required = table_meta.get("isRequired", "No").strip().lower() == "yes"

    lines = [f"  {class_name}:"]
    lines.append(f"    class_uri: omop:{class_name}")

    if table_desc and table_desc.upper() not in ("NA", ""):
        lines.append(f"    description: {_yaml_str(table_desc)}")
    if user_guidance and user_guidance.upper() not in ("NA", ""):
        lines.append(f"    comments:")
        lines.append(f"      - {_yaml_str(user_guidance)}")

    # Mark CDM required tables with a subset tag
    if is_required:
        lines.append("    in_subset:")
        lines.append("      - required_table")

    lines.append(f"    annotations:")
    lines.append(f"      omop_schema: {schema_group}")

    lines.append("    attributes:")
    for field in fields:
        lines.append(_render_slot(field, class_name))

    return "\n".join(lines)


def _schema_header(
    schema_id_suffix: str,
    name: str,
    title: str,
    description: str,
    extra_imports: list[str] | None = None,
) -> str:
    imports_block = "  - linkml:types\n"
    if extra_imports:
        for imp in extra_imports:
            imports_block += f"  - {imp}\n"

    return f"""\
---
id: {SCHEMA_BASE_URI}{schema_id_suffix}
name: {name}
title: {title}
description: >-
  {description}
  Generated from OHDSI CommonDataModel v{OMOP_CDM_VERSION}.

license: MIT
version: "{OMOP_CDM_VERSION}"

prefixes:
  linkml: https://w3id.org/linkml/
  omop: https://athena.ohdsi.org/search-terms/terms#
  plugin_rosetta: {SCHEMA_BASE_URI}

default_prefix: {SCHEMA_BASE_URI}{schema_id_suffix}/
default_range: string

imports:
{imports_block}
subsets:
  required_table:
    description: >-
      OMOP CDM tables that must be present in a conformant database.

"""


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------
def generate() -> list[str]:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    table_meta = read_table_level()
    all_fields = read_field_level()

    # Bucket tables by their schema column
    buckets: dict[str, list[str]] = {"CDM": [], "VOCAB": [], "RESULTS": []}
    for table_name, meta in table_meta.items():
        schema_group = meta.get("schema", "CDM").strip()
        if schema_group in buckets:
            buckets[schema_group].append(table_name)
        else:
            buckets["CDM"].append(table_name)  # fallback

    schema_files = {
        "CDM": (
            "omop_cdm",
            "omop-cdm",
            "OMOP CDM Clinical Tables",
            "LinkML representation of OMOP CDM 5.4 clinical (CDM schema) tables.",
        ),
        "VOCAB": (
            "omop_vocabulary",
            "omop-vocabulary",
            "OMOP CDM Vocabulary Tables",
            "LinkML representation of OMOP CDM 5.4 vocabulary (VOCAB schema) tables.",
        ),
        "RESULTS": (
            "omop_results",
            "omop-results",
            "OMOP CDM Results Tables",
            "LinkML representation of OMOP CDM 5.4 results/cohort (RESULTS schema) tables.",
        ),
    }

    generated_files = []

    for schema_group, (
        file_stem,
        schema_id_suffix,
        title,
        description,
    ) in schema_files.items():
        table_names = buckets.get(schema_group, [])
        if not table_names:
            print(f"  Skipping {schema_group} - no tables found.")
            continue

        header = _schema_header(
            schema_id_suffix=schema_id_suffix,
            name=file_stem,
            title=title,
            description=description,
        )

        classes_block = "classes:\n\n"
        for table_name in table_names:
            meta = table_meta.get(table_name, {})
            fields = all_fields.get(table_name, [])
            if not fields:
                print(f"  Warning: no fields found for table '{table_name}', skipping.")
                continue
            classes_block += _render_class(table_name, meta, fields) + "\n\n"

        out_path = SCHEMA_DIR / f"{file_stem}.yaml"
        out_path.write_text(header + classes_block, encoding="utf-8")
        print(
            f"  Written: {out_path.relative_to(REPO_ROOT)} ({len(table_names)} tables)"
        )
        generated_files.append(file_stem)

    print(f"\nGenerated {len(generated_files)} OMOP schema files.")
    return generated_files


if __name__ == "__main__":
    print(f"Generating OMOP CDM LinkML schemas from OHDSI CSV sources...")
    generate()
    print("Done.")
