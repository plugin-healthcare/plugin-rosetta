from typing import TYPE_CHECKING

import pytest
import yaml

from plugin_rosetta.errors import RosettaIOError
from plugin_rosetta.workspace import initialize_workspace

if TYPE_CHECKING:
    from pathlib import Path


def test_initializes_empty_workspace_without_domain_specific_inputs(tmp_path: Path) -> None:
    destination = tmp_path / "workspace"

    config_path = initialize_workspace(destination)

    assert config_path == destination / "rosetta.yaml"
    workspace = yaml.safe_load(config_path.read_text())
    assert workspace == {
        "version": 1,
        "registry": "registry",
        "mapping_sets": [],
        "ontology_sources": [],
        "vocabulary_sources": [],
    }
    assert yaml.safe_load((destination / "registry/config/mapping-sets.yaml").read_text()) == {"mapping_sets": {}}
    assert yaml.safe_load((destination / "registry/config/ontology-sources.yaml").read_text()) == {
        "ontology_sources": {}
    }
    assert yaml.safe_load((destination / "registry/config/vocabulary-sources.yaml").read_text()) == {
        "vocabulary_sources": {}
    }
    assert (destination / "registry/data/.gitignore").is_file()


def test_init_refuses_to_overwrite_existing_workspace(tmp_path: Path) -> None:
    destination = tmp_path / "workspace"
    destination.mkdir()
    (destination / "rosetta.yaml").write_text("existing: true\n")

    with pytest.raises(RosettaIOError, match="already exists"):
        initialize_workspace(destination)

    assert (destination / "rosetta.yaml").read_text() == "existing: true\n"
