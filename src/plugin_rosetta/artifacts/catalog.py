"""Content-addressed local artifact catalogue."""

import errno
import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version as distribution_version
from pathlib import Path

from plugin_rosetta.artifacts.identity import ArtifactKind, canonical_bytes, content_version  # noqa: TC001
from plugin_rosetta.artifacts.manifest import ArtifactInput, ArtifactManifest  # noqa: TC001
from plugin_rosetta.errors import ArtifactError
from plugin_rosetta.utils.io.atomic import atomic_write_bytes, atomic_write_text
from plugin_rosetta.utils.source_names import validate_portable_source_name

DEFAULT_ARTIFACT_CATALOG = Path("registry/data/artifacts")


@dataclass(frozen=True)
class RegisteredArtifact:
    """Resolved paths and manifest for one catalogue entry."""

    artifact_path: Path
    manifest_path: Path
    manifest: ArtifactManifest

    @property
    def version(self) -> str:
        """Return the content-addressed version."""
        return self.manifest.version


def _entry_dir(catalog_dir: Path, name: str, artifact_version: str) -> Path:
    return catalog_dir / name / artifact_version


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
    """Register an immutable artifact version and return its catalogue entry."""
    try:
        validate_portable_source_name(name)
    except ValueError as error:
        raise ArtifactError(f"Invalid artifact name: {error}") from error
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
    """List registered versions in registration order with a stable tie-break."""
    root = catalog_dir / name
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
    """Resolve a named content version or raise an actionable error."""
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
    """Return every registered artifact that names the given input."""
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
