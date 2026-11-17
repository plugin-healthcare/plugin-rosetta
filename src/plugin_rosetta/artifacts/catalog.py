"""Content-addressed local artifact catalogue."""

import errno
import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version as distribution_version
from pathlib import Path

from plugin_rosetta.artifacts.identity import ArtifactKind, canonical_bytes, content_version
from plugin_rosetta.artifacts.manifest import ArtifactInput, ArtifactManifest
from plugin_rosetta.errors import ArtifactError
from plugin_rosetta.utils.io.atomic import atomic_write_bytes, atomic_write_text
from plugin_rosetta.utils.source_names import validate_portable_source_name

DEFAULT_ARTIFACT_CATALOG = Path("registry/data/artifacts")
"""Default catalogue directory, relative to the workspace root."""


@dataclass(frozen=True)
class RegisteredArtifact:
    """Resolved paths and manifest for one catalogue entry.

    Attributes:
        artifact_path: Path of the stored canonical artifact.
        manifest_path: Path of the `manifest.json` next to the artifact.
        manifest: The parsed manifest.
    """

    artifact_path: Path
    manifest_path: Path
    manifest: ArtifactManifest

    @property
    def version(self) -> str:
        """Return the 64-character SHA-256 version from the manifest."""
        return self.manifest.version


def _segment(label: str, value: str) -> str:
    try:
        return validate_portable_source_name(value)
    except ValueError as error:
        raise ArtifactError(f"Invalid artifact {label}: {error}") from error


def _entry_dir(catalog_dir: Path, name: str, artifact_version: str) -> Path:
    return catalog_dir / _segment("name", name) / _segment("version", artifact_version)


def _read_entry(entry_dir: Path) -> RegisteredArtifact:
    manifest_path = entry_dir / "manifest.json"
    try:
        manifest = ArtifactManifest.model_validate_json(manifest_path.read_text())
    except (OSError, ValueError) as error:
        raise ArtifactError(f"Cannot read artifact manifest {manifest_path}: {error}") from error
    return RegisteredArtifact(entry_dir / manifest.artifact_filename, manifest_path, manifest)


def _validate_existing(
    registered: RegisteredArtifact,
    *,
    kind: ArtifactKind,
    source_name: str,
    source_version: str,
    inputs: tuple[ArtifactInput, ...],
    key_columns: tuple[str, ...],
) -> RegisteredArtifact:
    existing = registered.manifest
    requested = (kind, source_name, source_version, inputs, key_columns)
    recorded = (existing.kind, existing.source_name, existing.source_version, existing.inputs, existing.key_columns)
    if recorded != requested:
        raise ArtifactError(
            f"Artifact {existing.name!r} version {existing.version!r} is already registered with different provenance"
        )
    return registered


def register_artifact(
    name: str,
    artifact_path: Path,
    kind: ArtifactKind,
    *,
    catalog_dir: Path = DEFAULT_ARTIFACT_CATALOG,
    source_name: str,
    source_version: str,
    inputs: tuple[ArtifactInput, ...] = (),
    key_columns: tuple[str, ...] = (),
) -> RegisteredArtifact:
    """Register an immutable artifact version and return its catalogue entry.

    The content is canonicalised for `kind` and stored with a manifest under
    `<catalog_dir>/<name>/<version>/`. Registering identical content again
    returns the existing entry if its provenance matches. Entries are never
    overwritten.

    Args:
        name: Portable lowercase artifact name, for example `omop-onz-g`.
        artifact_path: Path of the artifact file.
        kind: Artifact format.
        catalog_dir: Catalogue directory.
        source_name: Name of the source the artifact was built from.
        source_version: Version of that source.
        inputs: Artifacts or releases this artifact was derived from.
        key_columns: Row-identifying columns of a `table` artifact; needed to
            compare table versions.

    Returns:
        The catalogue entry of the new or existing version.

    Raises:
        ArtifactError: If `name` is invalid, the artifact cannot be read or
            parsed, an existing entry cannot be read or has different
            provenance, or the new entry cannot be published.
        RosettaIOError: If a file of the new entry cannot be written.
        OSError: If the catalogue directory or a temporary directory cannot
            be created.
    """
    _segment("name", name)
    try:
        content = artifact_path.read_bytes()
    except OSError as error:
        raise ArtifactError(f"Cannot read artifact {artifact_path}: {error}") from error
    artifact_version = content_version(kind, content)
    destination = _entry_dir(catalog_dir, name, artifact_version)
    if destination.is_dir():
        return _validate_existing(
            _read_entry(destination),
            kind=kind,
            source_name=source_name,
            source_version=source_version,
            inputs=inputs,
            key_columns=key_columns,
        )

    timestamp = datetime.now(UTC).isoformat()
    stored_filename = f"artifact{artifact_path.suffix}"
    manifest = ArtifactManifest(
        name=name,
        version=artifact_version,
        kind=kind,
        artifact_filename=stored_filename,
        source_name=source_name,
        source_version=source_version,
        inputs=inputs,
        key_columns=key_columns,
        tool_version=distribution_version("plugin-rosetta"),
        built_at=timestamp,
        registered_at=timestamp,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=f".{artifact_version}.") as temporary:
        temporary_dir = Path(temporary)
        atomic_write_bytes(temporary_dir / stored_filename, canonical_bytes(kind, content))
        atomic_write_text(
            temporary_dir / "manifest.json",
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        )
        try:
            temporary_dir.replace(destination)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} and destination.is_dir():
                return _validate_existing(
                    _read_entry(destination),
                    kind=kind,
                    source_name=source_name,
                    source_version=source_version,
                    inputs=inputs,
                    key_columns=key_columns,
                )
            raise ArtifactError(f"Cannot register artifact {name!r}: {error}") from error
    return _read_entry(destination)


def list_versions(
    name: str,
    *,
    catalog_dir: Path = DEFAULT_ARTIFACT_CATALOG,
) -> tuple[ArtifactManifest, ...]:
    """List the manifests of all versions of an artifact.

    Args:
        name: Artifact name.
        catalog_dir: Catalogue directory.

    Returns:
        Manifests sorted by registration time, then version. Empty when
        nothing is registered under `name`.

    Raises:
        ArtifactError: If `name` is invalid or a manifest cannot be read.
    """
    root = catalog_dir / _segment("name", name)
    if not root.is_dir():
        return ()
    manifests = tuple(_read_entry(path).manifest for path in root.iterdir() if path.is_dir())
    return tuple(sorted(manifests, key=lambda item: (item.registered_at, item.version)))


def resolve_artifact(
    name: str,
    artifact_version: str,
    *,
    catalog_dir: Path = DEFAULT_ARTIFACT_CATALOG,
) -> RegisteredArtifact:
    """Return the catalogue entry of a registered version.

    Args:
        name: Artifact name.
        artifact_version: Content version returned at registration.
        catalog_dir: Catalogue directory.

    Raises:
        ArtifactError: If the name or version is invalid or not registered, or
            its manifest cannot be read.
    """
    destination = _entry_dir(catalog_dir, name, artifact_version)
    if destination.is_dir():
        return _read_entry(destination)
    known = sorted(path.name for path in catalog_dir.iterdir() if path.is_dir()) if catalog_dir.is_dir() else []
    known_text = ", ".join(known) or "none"
    raise ArtifactError(f"Unknown artifact {name!r} version {artifact_version!r}. Known artifacts: {known_text}")


def dependents(
    input_name: str,
    *,
    catalog_dir: Path = DEFAULT_ARTIFACT_CATALOG,
) -> tuple[ArtifactManifest, ...]:
    """Return the manifests of all artifacts that list the given input.

    Args:
        input_name: Name as recorded in `ArtifactInput.name`.
        catalog_dir: Catalogue directory.

    Returns:
        Manifests sorted by artifact name, registration time, and version.

    Raises:
        ArtifactError: If a manifest cannot be read.
    """
    if not catalog_dir.is_dir():
        return ()
    matches = [
        manifest
        for name_dir in catalog_dir.iterdir()
        if name_dir.is_dir()
        for manifest in list_versions(name_dir.name, catalog_dir=catalog_dir)
        if any(item.name == input_name for item in manifest.inputs)
    ]
    return tuple(sorted(matches, key=lambda item: (item.name, item.registered_at, item.version)))
