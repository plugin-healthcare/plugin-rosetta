"""Create an empty configurable Rosetta workspace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from plugin_rosetta.errors import RosettaIOError
from plugin_rosetta.utils.io.atomic import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


class WorkspaceConfig(BaseModel):
    """Selections and registry location for one initialized workspace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    registry: str = "registry"
    mapping_sets: tuple[str, ...] = ()
    ontology_sources: tuple[str, ...] = ()
    vocabulary_sources: tuple[str, ...] = ()


def _dump_yaml(value: object) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def initialize_workspace(destination: Path) -> Path:
    """Create an empty workspace ready for user-supplied registry inputs."""
    config_path = destination / "rosetta.yaml"
    registry_dir = destination / "registry"
    if config_path.exists() or registry_dir.exists():
        raise RosettaIOError(f"Rosetta workspace already exists at {destination}")

    files_to_write = {
        registry_dir / "config/mapping-sets.yaml": _dump_yaml({"mapping_sets": {}}),
        registry_dir / "config/ontology-sources.yaml": _dump_yaml({"ontology_sources": {}}),
        registry_dir / "config/vocabulary-sources.yaml": _dump_yaml({"vocabulary_sources": {}}),
        registry_dir / "data/.gitignore": "*\n!.gitignore\n!README.md\n",
        registry_dir / "data/README.md": "Downloaded, licensed, cached, and generated data belongs here.\n",
    }
    workspace = WorkspaceConfig()
    files_to_write[config_path] = _dump_yaml(workspace.model_dump(mode="json"))

    for path, content in files_to_write.items():
        atomic_write_text(path, content)
    return config_path
