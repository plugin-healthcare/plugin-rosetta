"""Reusable checksum-verified HTTP download to a local cache."""

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from plugin_rosetta.errors import RosettaIOError, ValidationError
from plugin_rosetta.reports import IssueSeverity, ValidationIssue
from plugin_rosetta.utils.io.atomic import atomic_write_bytes

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_TIMEOUT = 60


@dataclass(frozen=True)
class DownloadResult:
    """A downloaded file's cache path and any non-fatal checksum finding."""

    path: Path
    issue: ValidationIssue | None


def download_to_cache(
    url: str,
    destination: Path,
    *,
    expected_checksum: str | None = None,
    label: str | None = None,
    client: httpx.Client | None = None,
) -> DownloadResult:
    """Download `url`, verify its checksum, and write it atomically to `destination`.

    If `expected_checksum` is set, a mismatch raises before anything is
    written, so no partial file is ever left in the cache. If it is unset,
    the download proceeds and a warning `ValidationIssue` reports the
    computed SHA-256 so it can be backfilled into the source configuration.
    """
    display_label = label or url
    owns_client = client is None
    http_client = client or httpx.Client(timeout=_DEFAULT_TIMEOUT)
    try:
        response = http_client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise RosettaIOError(f"Failed to fetch {display_label}: {error}") from error
    finally:
        if owns_client:
            http_client.close()

    content = response.content
    digest = hashlib.sha256(content).hexdigest()

    issue = None
    if expected_checksum is None:
        issue = ValidationIssue(
            code="ontology.missing-checksum",
            severity=IssueSeverity.WARNING,
            location=display_label,
            message=f"No checksum pinned for {display_label!r}; computed SHA-256 {digest}.",
        )
    elif digest != expected_checksum:
        raise ValidationError(f"Checksum mismatch for {display_label!r}: expected {expected_checksum}, got {digest}")

    atomic_write_bytes(destination, content)
    return DownloadResult(path=destination, issue=issue)
