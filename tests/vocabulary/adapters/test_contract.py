import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plugin_rosetta.vocabulary.adapters import get_build_adapter

ROOT = Path(__file__).parents[3]
CONFIG_PATH = ROOT / "registry/config/vocabulary-sources.yaml"


@pytest.mark.parametrize(
    ("adapter_name", "release_dir", "as_of"),
    [
        ("omop", ROOT / "tests/fixtures/vocabulary/athena", None),
        ("dhd-diagnosethesaurus", ROOT / "tests/fixtures/vocabulary/dhd", "20260910"),
        ("dhd-verrichtingenthesaurus", ROOT / "tests/fixtures/vocabulary/dhd", "20260910"),
    ],
)
def test_build_adapters_write_turtle_and_provenance_through_one_contract(
    tmp_path: Path,
    adapter_name: str,
    release_dir: Path,
    as_of: str | None,
) -> None:
    adapter = get_build_adapter(adapter_name)

    turtle_path, metadata_path = adapter.build(
        release_dir,
        tmp_path,
        config_path=CONFIG_PATH,
        as_of=as_of,
    )

    assert turtle_path.is_file()
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "from rdflib import Graph; import sys; print(len(Graph().parse(sys.argv[1], format='turtle')))",
            str(turtle_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert int(result.stdout) > 0
    metadata = json.loads(metadata_path.read_text())
    assert metadata["source_name"] == adapter.source_name
    assert metadata["as_of"] == as_of


def test_get_build_adapter_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Known build adapters"):
        get_build_adapter("unknown")


def _configured_registry(tmp_path: Path, old: str, new: str) -> Path:
    registry = tmp_path / "registry"
    shutil.copytree(ROOT / "registry/schemas", registry / "schemas")
    config_path = registry / "config/vocabulary-sources.yaml"
    config_path.parent.mkdir()
    content = (ROOT / "registry/config/vocabulary-sources.yaml").read_text()
    config_path.write_text(content.replace(old, new, 1))
    return config_path


def test_omop_adapter_uses_configured_filename_instead_of_hardcoded_name(tmp_path: Path) -> None:
    release_dir = tmp_path / "omop"
    shutil.copytree(ROOT / "tests/fixtures/vocabulary/athena", release_dir)
    (release_dir / "CONCEPT.csv").rename(release_dir / "RENAMED_CONCEPTS.tsv")
    config_path = _configured_registry(tmp_path, "name: CONCEPT.csv", "name: RENAMED_CONCEPTS.tsv")

    turtle_path, _ = get_build_adapter("omop").build(
        release_dir,
        tmp_path / "output",
        config_path=config_path,
        as_of=None,
    )

    assert turtle_path.is_file()


def test_thesaurus_adapter_uses_configured_suffix_instead_of_hardcoded_name(tmp_path: Path) -> None:
    release_dir = tmp_path / "dhd"
    shutil.copytree(ROOT / "tests/fixtures/vocabulary/dhd", release_dir)
    concept_dir = release_dir / "thesauri/DT/202609_uitleverformaat4.3"
    (concept_dir / "SYN_ThesaurusConcept.csv").rename(concept_dir / "SYN_RenamedConcepts.csv")
    config_path = _configured_registry(
        tmp_path,
        "suffix: _ThesaurusConcept.csv",
        "suffix: _RenamedConcepts.csv",
    )

    turtle_path, _ = get_build_adapter("dhd-diagnosethesaurus").build(
        release_dir,
        tmp_path / "output",
        config_path=config_path,
        as_of="20260910",
    )

    assert turtle_path.is_file()
