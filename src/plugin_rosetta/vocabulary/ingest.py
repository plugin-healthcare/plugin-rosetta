"""Safe ingestion of curator-provided vocabulary release ZIPs."""

from __future__ import annotations

import hashlib
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from plugin_rosetta.core.errors import VocabularyChecksumError, VocabularyIngestError
from plugin_rosetta.core.report import IssueSeverity, ValidationIssue, ValidationReport

if TYPE_CHECKING:
    from collections.abc import Callable

    from plugin_rosetta.config.vocabulary_sources import VocabularySource

DEFAULT_CACHE_DIR = Path("registry/data/vocabularies")
_FORMAT_VERSION_PATTERN = re.compile(r"uitleverformaat\d+(?:\.\d+)*", re.IGNORECASE)
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class IngestResult:
    """An ingested release directory and any non-fatal checksum finding."""

    path: Path
    issue: ValidationIssue | None
    validation_report: ValidationReport = field(default_factory=ValidationReport)


def cache_dir_for(source: VocabularySource, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Return the versioned extraction directory for a vocabulary source."""
    target_dir = cache_dir / source.name / source.version
    if not target_dir.resolve().is_relative_to(cache_dir.resolve()):
        raise VocabularyIngestError(
            f"Vocabulary cache path for source {source.name!r} resolves outside cache root {cache_dir}"
        )
    return target_dir


def _is_extracted(target_dir: Path) -> bool:
    return target_dir.is_dir() and any(path.is_file() for path in target_dir.rglob("*"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _member_path(info: zipfile.ZipInfo) -> PurePosixPath:
    normalized = info.filename.replace("\\", "/")
    path = PurePosixPath(normalized)
    mode = info.external_attr >> 16
    if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
        raise VocabularyIngestError(f"ZIP contains unsafe archive member {info.filename!r}")
    return path


def _validate_format_version(source: VocabularySource, members: tuple[PurePosixPath, ...]) -> None:
    expected = source.format_version
    if expected is None:
        return
    found = sorted({match.group(0) for member in members for match in _FORMAT_VERSION_PATTERN.finditer(str(member))})
    if expected.casefold() in {marker.casefold() for marker in found}:
        return
    found_text = ", ".join(found) if found else "none"
    raise VocabularyIngestError(
        f"Vocabulary source {source.name!r} expected format marker {expected!r}, found {found_text}"
    )


def _extract(
    archive: zipfile.ZipFile, members: tuple[tuple[zipfile.ZipInfo, PurePosixPath], ...], target: Path
) -> None:
    for info, relative_path in members:
        destination = target.joinpath(*relative_path.parts)
        if info.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source_stream, destination.open("wb") as destination_stream:
            shutil.copyfileobj(source_stream, destination_stream)


def _replace_directory(temporary_dir: Path, target_dir: Path) -> None:
    if not target_dir.exists():
        temporary_dir.replace(target_dir)
        return

    backup_dir = target_dir.with_name(f".{target_dir.name}.backup-{uuid.uuid4().hex}")
    target_dir.replace(backup_dir)
    try:
        temporary_dir.replace(target_dir)
    except OSError:
        backup_dir.replace(target_dir)
        raise
    shutil.rmtree(backup_dir)


def _validate_extracted(
    target_dir: Path,
    validator: Callable[[Path], ValidationReport] | None,
) -> ValidationReport:
    if validator is None:
        return ValidationReport()
    report = validator(target_dir)
    if not report.is_valid:
        messages = "; ".join(issue.message for issue in report.issues if issue.severity is IssueSeverity.ERROR)
        raise VocabularyIngestError(f"Vocabulary release validation failed: {messages}")
    return report


def ingest_zip(
    source: VocabularySource,
    zip_path: Path,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    *,
    force: bool = False,
    validator: Callable[[Path], ValidationReport] | None = None,
) -> IngestResult:
    """Verify and atomically extract a local vocabulary release ZIP."""
    target_dir = cache_dir_for(source, cache_dir)
    if _is_extracted(target_dir) and not force:
        return IngestResult(path=target_dir, issue=None, validation_report=_validate_extracted(target_dir, validator))
    if not zip_path.is_file():
        raise VocabularyIngestError(f"ZIP not found: {zip_path}")

    try:
        digest = _sha256(zip_path)
    except OSError as error:
        raise VocabularyIngestError(f"Cannot read vocabulary ZIP {zip_path}: {error}") from error

    if source.checksum is not None and digest != source.checksum:
        raise VocabularyChecksumError(
            f"Checksum mismatch for vocabulary source {source.name!r}: expected {source.checksum}, actual {digest}"
        )

    issue = None
    if source.checksum is None:
        issue = ValidationIssue(
            code="vocabulary.missing-checksum",
            severity=IssueSeverity.WARNING,
            location=source.name,
            message=(f"No checksum pinned for vocabulary source {source.name!r}; computed SHA-256 {digest}."),
        )

    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = tuple((info, _member_path(info)) for info in archive.infolist())
            _validate_format_version(source, tuple(path for _, path in members))
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            temporary_dir = Path(tempfile.mkdtemp(prefix=f".{target_dir.name}.", dir=target_dir.parent))
            try:
                _extract(archive, members, temporary_dir)
                validation_report = _validate_extracted(temporary_dir, validator)
                _replace_directory(temporary_dir, target_dir)
            finally:
                if temporary_dir.exists():
                    shutil.rmtree(temporary_dir)
    except zipfile.BadZipFile as error:
        raise VocabularyIngestError(f"Not a valid ZIP: {zip_path}") from error
    except OSError as error:
        raise VocabularyIngestError(f"Cannot extract vocabulary ZIP {zip_path}: {error}") from error

    return IngestResult(path=target_dir, issue=issue, validation_report=validation_report)


def find_file(root: Path, *, prefix: str = "", suffix: str = "", contains: str = "") -> Path:
    """Find exactly one release file matching all supplied path filters."""
    matches = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name.startswith(prefix)
        and path.name.endswith(suffix)
        and contains in f"/{path.relative_to(root).as_posix()}"
    )
    search = f"prefix={prefix!r} suffix={suffix!r} contains={contains!r}"
    if not matches:
        raise VocabularyIngestError(f"No file matching {search} under {root}")
    if len(matches) > 1:
        joined = ", ".join(str(match) for match in matches)
        raise VocabularyIngestError(f"Expected exactly one file matching {search} under {root}, found: {joined}")
    return matches[0]
