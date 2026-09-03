"""Shared contracts and errors."""

from plugin_rosetta.core.errors import (
    ConfigurationError,
    RosettaError,
    RosettaIOError,
    ValidationError,
)
from plugin_rosetta.core.report import IssueSeverity, ValidationIssue, ValidationReport

__all__ = [
    "ConfigurationError",
    "IssueSeverity",
    "RosettaError",
    "RosettaIOError",
    "ValidationError",
    "ValidationIssue",
    "ValidationReport",
]
