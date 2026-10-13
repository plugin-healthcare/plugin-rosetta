"""Download-and-cache ontology loader."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rdflib import Graph
from rdflib.exceptions import ParserError

from plugin_rosetta.errors import RosettaIOError
from plugin_rosetta.ontology.download import download_to_cache

if TYPE_CHECKING:
    import httpx

    from plugin_rosetta.ontology.config import OntologySource
    from plugin_rosetta.reports import ValidationIssue

DEFAULT_CACHE_DIR = Path("registry/data/ontologies")
_HASH_CHUNK_SIZE = 1024 * 1024


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
        _verify_cached_checksum(path, source)
        return FetchResult(path=path, issue=None)
    result = download_to_cache(
        source.download_url,
        path,
        expected_checksum=source.checksum,
        label=source.name,
        client=client,
    )
    return FetchResult(path=result.path, issue=result.issue)


def _verify_cached_checksum(path: Path, source: OntologySource) -> None:
    if source.checksum is None:
        return
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(_HASH_CHUNK_SIZE), b""):
                digest.update(chunk)
    except OSError as error:
        raise RosettaIOError(f"Cannot read cached ontology {source.name!r} at {path}: {error}") from error
    actual = digest.hexdigest()
    if actual != source.checksum:
        raise RosettaIOError(
            f"Cached ontology {source.name!r} checksum mismatch: expected {source.checksum}, actual {actual}"
        )


def _parse_turtle(path: Path, name: str) -> Graph:
    graph = Graph()
    try:
        graph.parse(path, format="turtle")
    except (ParserError, SyntaxError) as error:
        raise RosettaIOError(f"Cannot parse ontology {name!r} at {path}: {error}") from error
    return graph


def load_ontology(
    source: OntologySource,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    client: httpx.Client | None = None,
) -> Graph:
    """Fetch (if needed) and parse an ontology source into an `rdflib.Graph`."""
    result = fetch_ontology(source, cache_dir=cache_dir, force=force, client=client)
    return _parse_turtle(result.path, source.name)


def load_cached_ontology(source: OntologySource, *, cache_dir: Path = DEFAULT_CACHE_DIR) -> Graph:
    """Parse an already-cached ontology without touching the network.

    Validation must never silently skip a check because the cache is empty, so
    a missing file tells the curator which fetch to run instead.
    """
    path = source.cache_path(cache_dir)
    if not path.is_file():
        raise RosettaIOError(
            f"Ontology {source.name!r} is not cached at {path}. Run: rosetta ontology fetch {source.name}"
        )
    _verify_cached_checksum(path, source)
    return _parse_turtle(path, source.name)
