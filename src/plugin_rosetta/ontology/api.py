"""Ontology source fetch use cases."""

from pathlib import Path
from typing import TYPE_CHECKING

from plugin_rosetta.ontology.config import load_ontology_sources
from plugin_rosetta.ontology.loader import DEFAULT_CACHE_DIR, fetch_ontology
from plugin_rosetta.reports import ValidationReport

if TYPE_CHECKING:
    import httpx

DEFAULT_ONTOLOGY_CONFIG = Path("registry/config/ontology-sources.yaml")
"""Default location of the ontology source configuration, relative to the workspace root."""


def fetch_ontology_source(
    name: str,
    *,
    config_path: Path = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    client: httpx.Client | None = None,
) -> tuple[Path, ValidationReport]:
    """Fetch and cache a configured ontology source.

    The file is stored at `<cache_dir>/<name>/<version>/ontology.ttl`. If it
    exists and `force` is false, no request is made and the cached file is
    verified against the pinned checksum, if any, and the report is empty. A
    download is verified before it is written. If a download has no pinned
    checksum, the report contains an `ontology.missing-checksum` warning with
    the computed SHA-256. The content is not parsed.

    Args:
        name: Name of the ontology source.
        config_path: Path to `ontology-sources.yaml`.
        cache_dir: Root directory of the ontology cache.
        force: Whether to download again even if the file is cached.
        client: HTTP client to use. A client with a 60 second timeout is
            created and closed when omitted.

    Returns:
        The path of the cached Turtle file and a report of non-fatal findings.

    Raises:
        ConfigurationError: If the configuration is invalid or `name` is unknown.
        RosettaIOError: If the download fails, a cached file fails its pinned
            checksum, or the file cannot be written.
        ValidationError: If the download does not match the pinned checksum.
    """
    source = load_ontology_sources(config_path).get(name)
    result = fetch_ontology(source, cache_dir=cache_dir, force=force, client=client)
    issues = (result.issue,) if result.issue is not None else ()
    return result.path, ValidationReport(issues=issues)
