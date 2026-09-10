"""Public local artifact registration and comparison API."""

from plugin_rosetta.artifacts.catalog import (
    DEFAULT_ARTIFACT_CATALOG,
    RegisteredArtifact,
    dependents,
    list_versions,
    register_artifact,
    resolve_artifact,
)
from plugin_rosetta.artifacts.diff import (
    ArtifactDifference,
    KeyedDifference,
    SchemaDifference,
    TripleDifference,
    diff_artifacts,
)
from plugin_rosetta.artifacts.identity import ArtifactKind, canonical_bytes, content_version
from plugin_rosetta.artifacts.manifest import ArtifactInput, ArtifactManifest

__all__ = [
    "DEFAULT_ARTIFACT_CATALOG",
    "ArtifactDifference",
    "ArtifactInput",
    "ArtifactKind",
    "ArtifactManifest",
    "KeyedDifference",
    "RegisteredArtifact",
    "SchemaDifference",
    "TripleDifference",
    "canonical_bytes",
    "content_version",
    "dependents",
    "diff_artifacts",
    "list_versions",
    "register_artifact",
    "resolve_artifact",
]
