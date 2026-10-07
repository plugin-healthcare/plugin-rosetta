"""Plain manifest models for registered local artifacts."""

from pydantic import BaseModel, ConfigDict

from plugin_rosetta.artifacts.identity import ArtifactKind  # noqa: TC001


class ArtifactInput(BaseModel):
    """One immutable input recorded by a derived artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    checksum: str


class ArtifactManifest(BaseModel):
    """Portable provenance and identity for one artifact version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    kind: ArtifactKind
    artifact_filename: str
    source_name: str
    source_version: str
    inputs: tuple[ArtifactInput, ...] = ()
    key_columns: tuple[str, ...] = ()
    tool_version: str
    built_at: str
    registered_at: str
