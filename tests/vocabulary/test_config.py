from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ConfigurationError
from plugin_rosetta.vocabulary import load_vocabulary_sources

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "registry/config/vocabulary-sources.yaml"


def test_loads_migrated_vocabulary_sources() -> None:
    config = load_vocabulary_sources(CONFIG_PATH)

    assert set(config.vocabulary_sources) == {
        "dhd-thesauri",
        "loinc-snomed",
        "omop",
        "snomed-international",
    }
    assert config.get("omop").download_page == "https://athena.ohdsi.org/"
    assert config.get("omop").tables[0].name == "CONCEPT.csv"
    assert config.get("loinc-snomed").kind == "rf2"
    assert config.get("snomed-international").version == "20260101"
    assert config.get("dhd-thesauri").format_version == "uitleverformaat4.3"


def test_vocabulary_source_is_frozen() -> None:
    source = load_vocabulary_sources(CONFIG_PATH).get("omop")

    with pytest.raises(PydanticValidationError):
        source.version = "2026"  # ty: ignore[invalid-assignment]


def test_unknown_vocabulary_source_lists_known_names() -> None:
    config = load_vocabulary_sources(CONFIG_PATH)

    with pytest.raises(
        ConfigurationError,
        match=r"Known vocabulary sources: dhd-thesauri, loinc-snomed, omop, snomed-international",
    ):
        config.get("missing")


@pytest.mark.parametrize("version", ["../escape", "has space", "with/slash"])
def test_rejects_filesystem_unsafe_version(tmp_path: Path, version: str) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace('version: "1.0"', f'version: "{version}"'))

    with pytest.raises(ConfigurationError, match="filesystem safe"):
        load_vocabulary_sources(config_path)


def test_rejects_invalid_checksum(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "    checksum: not-a-sha256\n")

    with pytest.raises(ConfigurationError, match="64-character lowercase SHA-256"):
        load_vocabulary_sources(config_path)


def test_rejects_filesystem_unsafe_source_name(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("  sample:", "  ../../outside:"))

    with pytest.raises(ConfigurationError, match="portable lowercase"):
        load_vocabulary_sources(config_path)


@pytest.mark.parametrize("name", ["OMOP", "CON", "source."])
def test_rejects_non_portable_vocabulary_source_name(tmp_path: Path, name: str) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("  sample:", f"  {name}:"))

    with pytest.raises(ConfigurationError, match="portable lowercase"):
        load_vocabulary_sources(config_path)


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    config_path = tmp_path / "vocabulary-sources.yaml"
    config_path.write_text(
        "vocabulary_sources:\n"
        "  sample:\n"
        '    version: "1.0"\n'
        "    kind: rf2\n"
        "    description: Synthetic source.\n"
        "    download_page: https://example.org/download\n"
        f"{extra}"
    )
    return config_path
