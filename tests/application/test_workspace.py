import json
from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from plugin_rosetta.application.workspace import (
    StarterSelection,
    initialize_workspace,
    list_starter_sources,
)
from plugin_rosetta.core.errors import ConfigurationError, RosettaIOError


def test_lists_packaged_starter_sources() -> None:
    sources = list_starter_sources()

    assert sources.mapping_sets == ("omop-onz-g",)
    assert sources.ontology_sources == ("omop-cdm", "onz-g")
    assert sources.vocabulary_sources == (
        "dhd-thesauri",
        "loinc-snomed",
        "omop",
        "snomed-international",
    )


def test_initializes_selected_workspace(tmp_path: Path) -> None:
    destination = tmp_path / "workspace"
    selection = StarterSelection(
        mapping_sets=("omop-onz-g",),
        ontology_sources=("omop-cdm",),
        vocabulary_sources=("omop",),
    )

    config_path = initialize_workspace(destination, selection)

    assert config_path == destination / "rosetta.yaml"
    workspace = yaml.safe_load(config_path.read_text())
    assert workspace == {
        "version": 1,
        "registry": "registry",
        "mapping_sets": ["omop-onz-g"],
        "ontology_sources": ["omop-cdm"],
        "vocabulary_sources": ["omop"],
    }
    assert (destination / "registry/mappings/omop-onz-g.csv").is_file()
    assert (destination / "registry/mappings/omop-onz-g.metadata.json").is_file()
    assert (destination / "registry/schemas/vocabularies/omop-concept.yaml").is_file()

    ontology_config = yaml.safe_load((destination / "registry/config/ontology-sources.yaml").read_text())
    vocabulary_config = yaml.safe_load((destination / "registry/config/vocabulary-sources.yaml").read_text())
    assert set(ontology_config["ontology_sources"]) == {"omop-cdm"}
    assert set(vocabulary_config["vocabulary_sources"]) == {"omop"}


def test_init_rejects_unknown_selection(tmp_path: Path) -> None:
    selection = StarterSelection(vocabulary_sources=("missing",))

    with pytest.raises(ConfigurationError, match="Unknown vocabulary source.*missing"):
        initialize_workspace(tmp_path / "workspace", selection)


def test_init_refuses_to_overwrite_existing_workspace(tmp_path: Path) -> None:
    destination = tmp_path / "workspace"
    destination.mkdir()
    (destination / "rosetta.yaml").write_text("existing: true\n")

    with pytest.raises(RosettaIOError, match="already exists"):
        initialize_workspace(destination, StarterSelection())

    assert (destination / "rosetta.yaml").read_text() == "existing: true\n"


@pytest.mark.parametrize(
    "relative_path",
    [
        "config/mapping-sets.yaml",
        "config/ontology-sources.yaml",
        "config/vocabulary-sources.yaml",
        "schemas/vocabularies/dhd-afleiding-dbc.yaml",
        "schemas/vocabularies/dhd-afleiding-icd10.yaml",
        "schemas/vocabularies/dhd-thesaurus-concept.yaml",
        "schemas/vocabularies/dhd-thesaurus-term.yaml",
        "schemas/vocabularies/omop-concept-relationship.yaml",
        "schemas/vocabularies/omop-concept.yaml",
        "schemas/vocabularies/omop-relationship.yaml",
        "schemas/vocabularies/rf2-concept.yaml",
    ],
)
def test_packaged_starter_yaml_matches_repository_registry(relative_path: str) -> None:
    packaged = files("plugin_rosetta.resources").joinpath("starter", "registry", *relative_path.split("/"))
    repository = Path(__file__).parents[2] / "registry" / relative_path

    assert yaml.safe_load(packaged.read_text()) == yaml.safe_load(repository.read_text())


def test_packaged_mapping_content_matches_repository_registry() -> None:
    packaged_root = files("plugin_rosetta.resources").joinpath("starter", "registry", "mappings")
    repository_root = Path(__file__).parents[2] / "registry/mappings"

    assert packaged_root.joinpath("omop-onz-g.csv").read_text() == (repository_root / "omop-onz-g.csv").read_text()
    assert json.loads(packaged_root.joinpath("omop-onz-g.metadata.json").read_text()) == json.loads(
        (repository_root / "omop-onz-g.metadata.json").read_text()
    )
