"""Download-and-cache ontology loader."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rdflib import Graph
from rdflib.exceptions import ParserError

from plugin_rosetta.core.errors import RosettaIOError
from plugin_rosetta.ontology.download import download_to_cache

if TYPE_CHECKING:
    import httpx

    from plugin_rosetta.config.ontology_sources import OntologySource
    from plugin_rosetta.core.report import ValidationIssue

DEFAULT_CACHE_DIR = Path("registry/data/ontologies")


@dataclass(frozen=True)
class FetchResult:
    """A fetched ontology's cache path and any non-fatal checksum finding."""

    path: Path
    issue: ValidationIssue | None


def fetch_ontology(
    source: OntologySource,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    client: httpx.Client | None = None,
) -> FetchResult:
    """Download and cache an ontology source's Turtle file.

    If the cached file already exists, the download is skipped (idempotent,
    no network call) unless `force` is True.
    """
    path = source.cache_path(cache_dir)
    if path.exists() and not force:
        return FetchResult(path=path, issue=None)
    result = download_to_cache(
        source.download_url,
        path,
        expected_checksum=source.checksum,
        label=source.name,
        client=client,
    )
    return FetchResult(path=result.path, issue=result.issue)


def load_ontology(
    source: OntologySource,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    client: httpx.Client | None = None,
) -> Graph:
    """Fetch (if needed) and parse an ontology source into an `rdflib.Graph`."""
    result = fetch_ontology(source, cache_dir=cache_dir, force=force, client=client)
    graph = Graph()
    try:
        graph.parse(result.path, format="turtle")
    except (ParserError, SyntaxError) as error:
        raise RosettaIOError(f"Cannot parse ontology {source.name!r} at {result.path}: {error}") from error
    return graph
