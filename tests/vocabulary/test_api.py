import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plugin_rosetta.errors import VocabularyError
from plugin_rosetta.vocabulary import build_dhd_graph, build_omop_graph

ROOT = Path(__file__).parents[2]
FIXTURE_DIR = ROOT / "tests/fixtures/vocabulary/athena"


def test_build_omop_graph_writes_parseable_turtle_and_provenance(tmp_path: Path) -> None:
    release_dir = tmp_path / "release"
    shutil.copytree(FIXTURE_DIR, release_dir)
    first_turtle, first_metadata = build_omop_graph(
        release_dir,
        tmp_path / "first",
        config_path=ROOT / "registry/config/vocabulary-sources.yaml",
    )
    second_turtle, _ = build_omop_graph(
        release_dir,
        tmp_path / "second",
        config_path=ROOT / "registry/config/vocabulary-sources.yaml",
    )

    assert first_turtle.read_bytes() == second_turtle.read_bytes()
    assert "@prefix omopconcept:" in first_turtle.read_text()
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "from rdflib import Graph; import sys; print(len(Graph().parse(sys.argv[1], format='turtle')))",
            str(first_turtle),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert int(result.stdout) > 0
    metadata = json.loads(first_metadata.read_text())
    assert metadata["source_name"] == "omop"
    assert metadata["source_version"] == "unversioned"
    assert metadata["format_version"] is None
    assert metadata["built_at"].endswith("+00:00")


@pytest.mark.parametrize("create_release_dir", [False, True])
def test_build_omop_graph_names_missing_release_and_ingest_command(
    tmp_path: Path,
    *,
    create_release_dir: bool,
) -> None:
    release_dir = tmp_path / "missing"
    if create_release_dir:
        release_dir.mkdir()

    with pytest.raises(VocabularyError, match=r"missing.*rosetta vocabulary ingest omop <zip>"):
        build_omop_graph(
            release_dir,
            tmp_path / "output",
            config_path=ROOT / "registry/config/vocabulary-sources.yaml",
        )

    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    ("thesaurus", "filename"),
    [
        ("dt", "dhd-diagnosethesaurus.ttl"),
        ("vt", "dhd-verrichtingenthesaurus.ttl"),
    ],
)
def test_build_dhd_graph_writes_deterministic_turtle_and_as_of_provenance(
    tmp_path: Path,
    thesaurus: str,
    filename: str,
) -> None:
    first_turtle, first_metadata = build_dhd_graph(
        ROOT / "tests/fixtures/vocabulary/dhd",
        tmp_path / "first",
        thesaurus,
        as_of="20260910",
        config_path=ROOT / "registry/config/vocabulary-sources.yaml",
    )
    second_turtle, _ = build_dhd_graph(
        ROOT / "tests/fixtures/vocabulary/dhd",
        tmp_path / "second",
        thesaurus,
        as_of="20260910",
        config_path=ROOT / "registry/config/vocabulary-sources.yaml",
    )

    assert first_turtle.name == filename
    assert first_turtle.read_bytes() == second_turtle.read_bytes()
    metadata = json.loads(first_metadata.read_text())
    assert metadata["source_name"] == "dhd-thesauri"
    assert metadata["source_version"] == "202508"
    assert metadata["format_version"] == "uitleverformaat4.3"
    assert metadata["as_of"] == "20260910"
