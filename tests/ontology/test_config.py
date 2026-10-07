from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ConfigurationError
from plugin_rosetta.ontology import load_ontology_sources

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "registry/config/ontology-sources.yaml"


def test_loads_migrated_ontology_sources() -> None:
    config = load_ontology_sources(CONFIG_PATH)

    assert set(config.ontology_sources) == {"onz-g", "omop-cdm"}

    omop_cdm = config.get("omop-cdm")
    assert omop_cdm.name == "omop-cdm"
    assert omop_cdm.version == "5.4"
    assert omop_cdm.iri == "https://w3id.org/omop/ontology"
    assert omop_cdm.download_url == (
        "https://raw.githubusercontent.com/plugin-healthcare/omop-cdm-owl/"
        "99d42596d675f0905724883fd35a81775f98bfe5/omop_cdm_v5.ttl"
    )
    assert omop_cdm.checksum is None

    onz_g = config.get("onz-g")
    assert onz_g.name == "onz-g"
    assert onz_g.version == "2.8.1"
    assert onz_g.iri == "http://purl.org/ozo/onz-g"


def test_ontology_source_is_frozen() -> None:
    source = load_ontology_sources(CONFIG_PATH).get("onz-g")

    with pytest.raises(PydanticValidationError):
        source.version = "9.9.9"  # ty: ignore[invalid-assignment]


def test_unknown_ontology_source_lists_known_names() -> None:
    config = load_ontology_sources(CONFIG_PATH)

    with pytest.raises(ConfigurationError, match=r"Known ontology sources: omop-cdm, onz-g"):
        config.get("missing")


def test_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "    unexpected: value\n")

    with pytest.raises(ConfigurationError, match="unexpected"):
        load_ontology_sources(config_path)


def test_rejects_relative_iri(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("iri: https://example.org/sample", "iri: sample"))

    with pytest.raises(ConfigurationError, match="absolute IRI"):
        load_ontology_sources(config_path)


@pytest.mark.parametrize("version", ["../escape", "has space", "with/slash"])
def test_rejects_filesystem_unsafe_version(tmp_path: Path, version: str) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace('version: "1.0"', f'version: "{version}"'))

    with pytest.raises(ConfigurationError, match="filesystem safe"):
        load_ontology_sources(config_path)


def test_rejects_duplicate_ontology_source_keys(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text() + config_path.read_text().split("ontology_sources:\n", maxsplit=1)[1]
    )

    with pytest.raises(ConfigurationError, match="duplicate key: sample"):
        load_ontology_sources(config_path)


def test_rejects_filesystem_unsafe_ontology_source_name(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("  sample:", "  ../../outside:"))

    with pytest.raises(ConfigurationError, match="portable lowercase"):
        load_ontology_sources(config_path)


@pytest.mark.parametrize("name", ["OMOP", "CON", "source."])
def test_rejects_non_portable_ontology_source_name(tmp_path: Path, name: str) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("  sample:", f"  {name}:"))

    with pytest.raises(ConfigurationError, match="portable lowercase"):
        load_ontology_sources(config_path)


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    config_path = tmp_path / "ontology-sources.yaml"
    config_path.write_text(
        "ontology_sources:\n"
        "  sample:\n"
        '    version: "1.0"\n'
        "    iri: https://example.org/sample\n"
        "    download_url: https://example.org/sample.ttl\n"
        f"{extra}"
    )
    return config_path
