"""Tools for authoring and publishing open mapping artifacts."""

from importlib.metadata import version

from plugin_rosetta.errors import (
    ArtifactError,
    ConfigurationError,
    RosettaError,
    RosettaIOError,
    UnresolvableCurieError,
    ValidationError,
    VocabularyChecksumError,
    VocabularyError,
    VocabularyIngestError,
)
from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport

__version__ = version("plugin-rosetta")

__all__ = [
    "ArtifactError",
    "ConfigurationError",
    "IssueSeverity",
    "RosettaError",
    "RosettaIOError",
    "UnresolvableCurieError",
    "ValidationError",
    "ValidationIssue",
    "ValidationReport",
    "VocabularyChecksumError",
    "VocabularyError",
    "VocabularyIngestError",
    "__version__",
]
