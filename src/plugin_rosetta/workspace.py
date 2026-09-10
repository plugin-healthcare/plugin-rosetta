"""Create a configured Rosetta workspace from packaged starter resources."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from plugin_rosetta.errors import ConfigurationError, RosettaIOError
from plugin_rosetta.utils.io.atomic import atomic_write_text

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable
    from pathlib import Path

_STARTER_PACKAGE = "plugin_rosetta.resources"
_STARTER_ROOT = "starter"


class StarterSelection(BaseModel):
    """Selected starter content for a new workspace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mapping_sets: tuple[str, ...] = ()
    ontology_sources: tuple[str, ...] = ()
    vocabulary_sources: tuple[str, ...] = ()


class StarterSources(BaseModel):
    """Names available from the packaged starter catalogue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mapping_sets: tuple[str, ...]
    ontology_sources: tuple[str, ...]
    vocabulary_sources: tuple[str, ...]


class WorkspaceConfig(BaseModel):
    """Selections and registry location for one initialized workspace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    registry: str = "registry"
    mapping_sets: tuple[str, ...] = ()
    ontology_sources: tuple[str, ...] = ()
    vocabulary_sources: tuple[str, ...] = ()


def _starter_file(relative_path: str) -> Traversable:
    return files(_STARTER_PACKAGE).joinpath(_STARTER_ROOT, *relative_path.split("/"))


def _load_starter_mapping(relative_path: str) -> dict[str, object]:
    resource = _starter_file(relative_path)
    try:
        value = yaml.safe_load(resource.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise RosettaIOError(f"Cannot read packaged starter resource {relative_path}: {error}") from error
    if not isinstance(value, dict):
        raise ConfigurationError(f"Packaged starter resource {relative_path} must contain a YAML mapping")
    return value


def list_starter_sources() -> StarterSources:
    """Return selectable names from the packaged starter catalogue."""
    mappings = _load_starter_mapping("registry/config/mapping-sets.yaml")["mapping_sets"]
    ontologies = _load_starter_mapping("registry/config/ontology-sources.yaml")["ontology_sources"]
    vocabularies = _load_starter_mapping("registry/config/vocabulary-sources.yaml")["vocabulary_sources"]
    if not isinstance(mappings, dict) or not isinstance(ontologies, dict) or not isinstance(vocabularies, dict):
        raise ConfigurationError("Packaged starter source catalogues must contain mappings")
    return StarterSources(
        mapping_sets=tuple(sorted(mappings)),
        ontology_sources=tuple(sorted(ontologies)),
        vocabulary_sources=tuple(sorted(vocabularies)),
    )


def _select_entries(
    config: dict[str, object],
    section: str,
    selected: tuple[str, ...],
    label: str,
) -> dict[str, object]:
    entries = config.get(section)
    if not isinstance(entries, dict):
        raise ConfigurationError(f"Packaged starter configuration has no {section!r} mapping")
    unknown = sorted(set(selected) - set(entries))
    if unknown:
        known = ", ".join(sorted(entries))
        raise ConfigurationError(f"Unknown {label} {', '.join(unknown)}. Known names: {known}")
    return {section: {name: entries[name] for name in selected}}


def _dump_yaml(value: object) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def _read_starter_text(relative_path: str) -> str:
    resource = _starter_file(relative_path)
    try:
        return resource.read_text()
    except OSError as error:
        raise RosettaIOError(f"Cannot read packaged starter resource {relative_path}: {error}") from error


def initialize_workspace(destination: Path, selection: StarterSelection) -> Path:
    """Create a workspace registry containing only the selected starter content."""
    config_path = destination / "rosetta.yaml"
    registry_dir = destination / "registry"
    if config_path.exists() or registry_dir.exists():
        raise RosettaIOError(f"Rosetta workspace already exists at {destination}")

    mapping_config = _select_entries(
        _load_starter_mapping("registry/config/mapping-sets.yaml"),
        "mapping_sets",
        selection.mapping_sets,
        "mapping set",
    )
    ontology_config = _select_entries(
        _load_starter_mapping("registry/config/ontology-sources.yaml"),
        "ontology_sources",
        selection.ontology_sources,
        "ontology source",
    )
    vocabulary_config = _select_entries(
        _load_starter_mapping("registry/config/vocabulary-sources.yaml"),
        "vocabulary_sources",
        selection.vocabulary_sources,
        "vocabulary source",
    )

    files_to_write = {
        registry_dir / "config/mapping-sets.yaml": _dump_yaml(mapping_config),
        registry_dir / "config/ontology-sources.yaml": _dump_yaml(ontology_config),
        registry_dir / "config/vocabulary-sources.yaml": _dump_yaml(vocabulary_config),
        registry_dir / "data/.gitignore": "*\n!.gitignore\n!README.md\n",
        registry_dir / "data/README.md": "Downloaded, licensed, cached, and generated data belongs here.\n",
    }
    mapping_entries = mapping_config["mapping_sets"]
    assert isinstance(mapping_entries, dict)
    for entry in mapping_entries.values():
        assert isinstance(entry, dict)
        for field in ("mapping_file", "metadata_file"):
            relative_path = str(entry[field]).removeprefix("registry/")
            files_to_write[registry_dir / relative_path] = _read_starter_text(f"registry/{relative_path}")

    vocabulary_entries = vocabulary_config["vocabulary_sources"]
    assert isinstance(vocabulary_entries, dict)
    contract_paths = {
        str(table["contract"])
        for entry in vocabulary_entries.values()
        if isinstance(entry, dict)
        for table in entry.get("tables", [])
        if isinstance(table, dict)
    }
    for relative_path in sorted(contract_paths):
        files_to_write[registry_dir / relative_path] = _read_starter_text(f"registry/{relative_path}")

    workspace = WorkspaceConfig(
        mapping_sets=selection.mapping_sets,
        ontology_sources=selection.ontology_sources,
        vocabulary_sources=selection.vocabulary_sources,
    )
    files_to_write[config_path] = _dump_yaml(workspace.model_dump(mode="json"))

    for path, content in files_to_write.items():
        atomic_write_text(path, content)
    return config_path
