"""Public ontology source fetch, cache, and load API."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from plugin_rosetta.ontology.api import DEFAULT_ONTOLOGY_CONFIG, fetch_ontology_source
    from plugin_rosetta.ontology.config import (
        OntologySource,
        OntologySourceEntry,
        OntologySourcesConfig,
        load_ontology_sources,
    )

__all__ = [
    "DEFAULT_ONTOLOGY_CONFIG",
    "OntologySource",
    "OntologySourceEntry",
    "OntologySourcesConfig",
    "fetch_ontology_source",
    "load_ontology_sources",
]

_EXPORT_MODULES = {
    "DEFAULT_ONTOLOGY_CONFIG": "plugin_rosetta.ontology.api",
    "OntologySource": "plugin_rosetta.ontology.config",
    "OntologySourceEntry": "plugin_rosetta.ontology.config",
    "OntologySourcesConfig": "plugin_rosetta.ontology.config",
    "fetch_ontology_source": "plugin_rosetta.ontology.api",
    "load_ontology_sources": "plugin_rosetta.ontology.config",
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
