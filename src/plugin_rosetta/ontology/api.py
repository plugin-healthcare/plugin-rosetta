"""Ontology source fetch use cases."""

from pathlib import Path
from typing import TYPE_CHECKING

from plugin_rosetta.ontology.config import load_ontology_sources
from plugin_rosetta.ontology.loader import DEFAULT_CACHE_DIR, fetch_ontology
from plugin_rosetta.reports import ValidationReport

if TYPE_CHECKING:
    import httpx

DEFAULT_ONTOLOGY_CONFIG = Path("registry/config/ontology-sources.yaml")


def fetch_ontology_source(
    name: str,
    *,
    config_path: Path = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    client: httpx.Client | None = None,
) -> tuple[Path, ValidationReport]:
    """Fetch and cache a configured ontology source, reporting non-fatal findings."""
    source = load_ontology_sources(config_path).get(name)
    result = fetch_ontology(source, cache_dir=cache_dir, force=force, client=client)
    issues = (result.issue,) if result.issue is not None else ()
    return result.path, ValidationReport(issues=issues)
