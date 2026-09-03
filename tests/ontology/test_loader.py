from typing import TYPE_CHECKING

import httpx
import pytest
from rdflib import Graph

from plugin_rosetta.config.ontology_sources import OntologySource
from plugin_rosetta.core.errors import RosettaIOError
from plugin_rosetta.ontology.loader import fetch_ontology, load_ontology

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

TURTLE = b"@prefix ex: <https://example.org/> .\nex:a a ex:Thing .\n"

SOURCE = OntologySource(
    name="sample",
    version="1.0",
    iri="https://example.org/sample",
    download_url="https://example.org/sample.ttl",
)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_downloads_into_name_version_cache_path(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=TURTLE)

    result = fetch_ontology(SOURCE, cache_dir=tmp_path, client=_client(handler))

    assert result.path == tmp_path / "sample" / "1.0" / "ontology.ttl"
    assert result.path.read_bytes() == TURTLE


def test_fetch_skips_download_on_cache_hit(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=TURTLE)

    cache_path = tmp_path / "sample" / "1.0" / "ontology.ttl"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(TURTLE)

    result = fetch_ontology(SOURCE, cache_dir=tmp_path, client=_client(handler))

    assert calls == []
    assert result.issue is None


def test_fetch_force_redownloads(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=TURTLE)

    cache_path = tmp_path / "sample" / "1.0" / "ontology.ttl"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"stale")

    fetch_ontology(SOURCE, cache_dir=tmp_path, force=True, client=_client(handler))

    assert len(calls) == 1
    assert cache_path.read_bytes() == TURTLE


def test_fetch_network_error_raises(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(RosettaIOError, match="Failed to fetch"):
        fetch_ontology(SOURCE, cache_dir=tmp_path, client=_client(handler))


def test_load_ontology_parses_cached_turtle(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=TURTLE)

    graph = load_ontology(SOURCE, cache_dir=tmp_path, client=_client(handler))

    assert isinstance(graph, Graph)
    assert len(graph) == 1


def test_load_ontology_raises_on_invalid_turtle(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not turtle {{{")

    with pytest.raises(RosettaIOError, match="Cannot parse"):
        load_ontology(SOURCE, cache_dir=tmp_path, client=_client(handler))
