from pathlib import Path

import httpx

from plugin_rosetta.application.ontology import fetch_ontology_source

TURTLE = b"@prefix ex: <https://example.org/> .\nex:a a ex:Thing .\n"
CONFIG_PATH = Path(__file__).parents[2] / "registry/config/ontology-sources.yaml"


def test_fetch_ontology_source_caches_and_reports_missing_checksum(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=TURTLE)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    path, report = fetch_ontology_source(
        "omop-cdm",
        config_path=CONFIG_PATH,
        cache_dir=tmp_path,
        client=client,
    )

    assert path == tmp_path / "omop-cdm" / "5.4" / "ontology.ttl"
    assert path.read_bytes() == TURTLE
    assert len(report.issues) == 1
    assert "No checksum pinned" in report.issues[0].message


def test_fetch_ontology_source_skips_download_on_cache_hit(tmp_path: Path) -> None:
    cache_path = tmp_path / "omop-cdm" / "5.4" / "ontology.ttl"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(TURTLE)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("no network call expected on cache hit")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    path, report = fetch_ontology_source(
        "omop-cdm",
        config_path=CONFIG_PATH,
        cache_dir=tmp_path,
        client=client,
    )

    assert path == cache_path
    assert report.issues == ()
