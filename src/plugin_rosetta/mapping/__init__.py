"""Public mapping authoring, validation, and reporting API."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from plugin_rosetta.mapping.api import (
        DEFAULT_MAPPING_CONFIG,
        MappingReadResult,
        build_mapping_artifacts,
        read_mapping_set,
        report_mapping_set,
    )
    from plugin_rosetta.mapping.config import (
        MappingSetConfig,
        MappingSetOntologies,
        MappingSetsConfig,
        load_mapping_sets,
    )
    from plugin_rosetta.mapping.registry import list_mapping_sets

__all__ = [
    "DEFAULT_MAPPING_CONFIG",
    "MappingReadResult",
    "MappingSetConfig",
    "MappingSetOntologies",
    "MappingSetsConfig",
    "build_mapping_artifacts",
    "list_mapping_sets",
    "load_mapping_sets",
    "read_mapping_set",
    "report_mapping_set",
]

_EXPORT_MODULES = {
    "DEFAULT_MAPPING_CONFIG": "plugin_rosetta.mapping.api",
    "MappingReadResult": "plugin_rosetta.mapping.api",
    "MappingSetConfig": "plugin_rosetta.mapping.config",
    "MappingSetOntologies": "plugin_rosetta.mapping.config",
    "MappingSetsConfig": "plugin_rosetta.mapping.config",
    "build_mapping_artifacts": "plugin_rosetta.mapping.api",
    "list_mapping_sets": "plugin_rosetta.mapping.registry",
    "load_mapping_sets": "plugin_rosetta.mapping.config",
    "read_mapping_set": "plugin_rosetta.mapping.api",
    "report_mapping_set": "plugin_rosetta.mapping.api",
}


def __getattr__(name: str) -> Any:
    """Load public exports without coupling internal module initialization."""
    try:
        module_name = _EXPORT_MODULES[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
