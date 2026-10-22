"""Plain manifest models for registered local artifacts."""

from pydantic import BaseModel, ConfigDict

from plugin_rosetta.artifacts.identity import ArtifactKind


class ArtifactInput(BaseModel):
    """One immutable input recorded by a derived artifact.

    Attributes:
        name: Input name, for example an artifact or vocabulary source name.
        version: Version of the input.
        checksum: Checksum as supplied by the caller; not verified.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    checksum: str


class ArtifactManifest(BaseModel):
    """Portable provenance and identity for one artifact version.

    The manifest is stored as `manifest.json` next to the artifact.

    Attributes:
        name: Artifact name.
        version: Content version computed by `content_version`.
        kind: Artifact format.
        artifact_filename: File name of the stored artifact.
        source_name: Name of the source the artifact was built from.
        source_version: Version of that source.
        inputs: Inputs the artifact was derived from.
        key_columns: Row-identifying columns of a `table` artifact.
        tool_version: plugin-rosetta version that registered the artifact.
        built_at: ISO 8601 UTC build timestamp.
        registered_at: ISO 8601 UTC registration timestamp.
    """

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
