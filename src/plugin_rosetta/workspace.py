"""Create an empty configurable Rosetta workspace.

A workspace is a directory with a `rosetta.yaml` file and a `registry/` tree
holding YAML configuration and a `data/` directory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from plugin_rosetta.errors import RosettaIOError
from plugin_rosetta.utils.io.atomic import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


class WorkspaceConfig(BaseModel):
    """Selections and registry location for one initialized workspace.

    This model describes the content of `rosetta.yaml`.

    Attributes:
        version: Schema version. Only `1` is accepted.
        registry: Registry directory, relative to the workspace root.
        mapping_sets: Keys from `mapping-sets.yaml`.
        ontology_sources: Names from `ontology-sources.yaml`.
        vocabulary_sources: Names from `vocabulary-sources.yaml`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    registry: str = "registry"
    mapping_sets: tuple[str, ...] = ()
    ontology_sources: tuple[str, ...] = ()
    vocabulary_sources: tuple[str, ...] = ()


def _dump_yaml(value: object) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def initialize_workspace(destination: Path) -> Path:
    """Create an empty workspace ready for user-supplied registry inputs.

    Writes `rosetta.yaml`, empty catalogues under `registry/config/`, and a
    `registry/data/` directory that keeps generated data out of version control.
    Existing workspaces are never overwritten.

    Args:
        destination: Directory to create the workspace in.

    Returns:
        Path to the new `rosetta.yaml`.

    Raises:
        RosettaIOError: If `rosetta.yaml` or `registry/` already exists, or a
            file cannot be written.
    """
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
