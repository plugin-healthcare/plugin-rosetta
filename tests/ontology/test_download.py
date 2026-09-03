import hashlib
from typing import TYPE_CHECKING

import httpx
import pytest

from plugin_rosetta.core.errors import RosettaIOError, ValidationError
from plugin_rosetta.core.report import IssueSeverity
from plugin_rosetta.ontology.download import download_to_cache

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

CONTENT = b"@prefix ex: <https://example.org/> .\n"
DIGEST = hashlib.sha256(CONTENT).hexdigest()


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_downloads_and_writes_to_cache(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.org/ontology.ttl"
        return httpx.Response(200, content=CONTENT)

    destination = tmp_path / "sample" / "1.0" / "ontology.ttl"

    result = download_to_cache(
        "https://example.org/ontology.ttl",
        destination,
        expected_checksum=DIGEST,
        client=_client(handler),
    )

    assert result.path == destination
    assert destination.read_bytes() == CONTENT
    assert result.issue is None


def test_missing_checksum_yields_warning_issue(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=CONTENT)

    destination = tmp_path / "ontology.ttl"

    result = download_to_cache(
        "https://example.org/ontology.ttl",
        destination,
        client=_client(handler),
    )

    assert result.issue is not None
    assert result.issue.severity is IssueSeverity.WARNING
    assert DIGEST in result.issue.message
    assert destination.is_file()


def test_checksum_mismatch_raises_and_leaves_no_partial_file(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=CONTENT)

    destination = tmp_path / "ontology.ttl"

    with pytest.raises(ValidationError, match=r"sample.*expected deadbeef.*got " + DIGEST) as error:
        download_to_cache(
            "https://example.org/ontology.ttl",
            destination,
            expected_checksum="deadbeef",
            label="sample",
            client=_client(handler),
        )

    assert "Checksum mismatch" in str(error.value)
    assert not destination.exists()


def test_network_error_raises_and_leaves_no_partial_file(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    destination = tmp_path / "ontology.ttl"

    with pytest.raises(RosettaIOError, match="Failed to fetch"):
        download_to_cache(
            "https://example.org/ontology.ttl",
            destination,
            client=_client(handler),
        )

    assert not destination.exists()


def test_http_error_status_raises(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    destination = tmp_path / "ontology.ttl"

    with pytest.raises(RosettaIOError, match="Failed to fetch"):
        download_to_cache(
            "https://example.org/ontology.ttl",
            destination,
            client=_client(handler),
        )

    assert not destination.exists()
