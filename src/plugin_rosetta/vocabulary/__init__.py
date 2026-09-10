"""Public vocabulary release ingestion, validation, and graph API."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary.api import (
        DEFAULT_VOCABULARY_CONFIG,
        DEFAULT_VOCABULARY_OUTPUT_DIR,
        build_cached_omop_graph,
        build_omop_graph,
        ingest_release,
    )
    from plugin_rosetta.vocabulary.config import (
        ReleaseTable,
        VocabularySource,
        VocabularySourceEntry,
        VocabularySourcesConfig,
        load_vocabulary_sources,
    )

__all__ = [
    "DEFAULT_VOCABULARY_CONFIG",
    "DEFAULT_VOCABULARY_OUTPUT_DIR",
    "ReleaseTable",
    "VocabularySource",
    "VocabularySourceEntry",
    "VocabularySourcesConfig",
    "build_cached_omop_graph",
    "build_omop_graph",
    "ingest_release",
    "load_vocabulary_sources",
]

_EXPORT_MODULES = {
    "DEFAULT_VOCABULARY_CONFIG": "plugin_rosetta.vocabulary.api",
    "DEFAULT_VOCABULARY_OUTPUT_DIR": "plugin_rosetta.vocabulary.api",
    "ReleaseTable": "plugin_rosetta.vocabulary.config",
    "VocabularySource": "plugin_rosetta.vocabulary.config",
    "VocabularySourceEntry": "plugin_rosetta.vocabulary.config",
    "VocabularySourcesConfig": "plugin_rosetta.vocabulary.config",
    "build_cached_omop_graph": "plugin_rosetta.vocabulary.api",
    "build_omop_graph": "plugin_rosetta.vocabulary.api",
    "ingest_release": "plugin_rosetta.vocabulary.api",
    "load_vocabulary_sources": "plugin_rosetta.vocabulary.config",
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
