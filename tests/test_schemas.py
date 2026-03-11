"""Tests for LinkML schema validity.

Verifies that all schema YAML files:
1. Are valid YAML.
2. Can be loaded by the LinkML runtime without errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

SCHEMA_DIR = Path(__file__).parent.parent / "src" / "plugin_rosetta" / "schema"

SCHEMA_FILES = [
    "omop_cdm.yaml",
    "omop_vocabulary.yaml",
    "omop_results.yaml",
    "fhir_resources.yaml",
    "plugin_rosetta.yaml",
]


@pytest.mark.parametrize("filename", SCHEMA_FILES)
def test_schema_is_valid_yaml(filename):
    """Each schema file must parse as valid YAML."""
    path = SCHEMA_DIR / filename
    assert path.exists(), f"Schema file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{filename} did not parse as a YAML mapping"
    assert "id" in data, f"{filename} missing top-level 'id' key"
    assert "name" in data, f"{filename} missing top-level 'name' key"


@pytest.mark.parametrize("filename", SCHEMA_FILES)
def test_schema_loads_with_linkml(filename):
    """Each schema file must load without error via linkml-runtime SchemaView."""
    pytest.importorskip("linkml_runtime", reason="linkml-runtime not installed")
    from linkml_runtime.utils.schemaview import SchemaView

    path = SCHEMA_DIR / filename
    sv = SchemaView(str(path))
    # Basic sanity: at least one class should be defined (or imported)
    all_classes = sv.all_classes()
    assert len(all_classes) > 0, f"{filename}: SchemaView found no classes"


def test_plugin_rosetta_imports_all_subschemas():
    """plugin_rosetta.yaml must import all four sub-schemas."""
    path = SCHEMA_DIR / "plugin_rosetta.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    imports = data.get("imports", [])
    for expected in ("omop_cdm", "omop_vocabulary", "omop_results", "fhir_resources"):
        assert any(expected in imp for imp in imports), (
            f"plugin_rosetta.yaml does not import '{expected}'"
        )


def test_fhir_resources_has_eight_resource_classes():
    """fhir_resources.yaml must contain the 8 expected FHIR resource classes."""
    path = SCHEMA_DIR / "fhir_resources.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    classes = data.get("classes", {})
    expected = {
        "Patient",
        "Encounter",
        "Condition",
        "Observation",
        "Procedure",
        "MedicationStatement",
        "Immunization",
        "AllergyIntolerance",
    }
    found = set(classes.keys())
    missing = expected - found
    assert not missing, f"fhir_resources.yaml missing classes: {missing}"
