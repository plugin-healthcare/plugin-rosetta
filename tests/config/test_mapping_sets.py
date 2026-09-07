from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.config.mapping_sets import load_mapping_sets
from plugin_rosetta.config.ontology_sources import load_ontology_sources
from plugin_rosetta.core.errors import ConfigurationError

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "registry/config/mapping-sets.yaml"


def test_loads_preserved_mapping_set_configuration() -> None:
    config = load_mapping_sets(CONFIG_PATH, root=ROOT)

    mapping_set = config.get("omop-onz-g")

    assert tuple(config.mapping_sets) == ("omop-onz-g",)
    assert mapping_set.mapping_set_id == (
        "https://raw.githubusercontent.com/plugin-healthcare/sssom-rosetta/main/build/mappings/omop-onz-g.sssom.tsv"
    )
    assert mapping_set.license == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert mapping_set.mapping_file == Path("registry/mappings/omop-onz-g.csv")
    assert mapping_set.metadata_file == Path("registry/mappings/omop-onz-g.metadata.json")
    assert mapping_set.curie_map == {
        "omop": "https://w3id.org/omop/ontology/",
        "onz-g": "http://purl.org/ozo/onz-g#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "semapv": "https://w3id.org/semapv/vocab/",
        "orcid": "https://orcid.org/",
    }


def test_mapping_set_configuration_is_frozen() -> None:
    mapping_set = load_mapping_sets(CONFIG_PATH, root=ROOT).get("omop-onz-g")

    with pytest.raises(PydanticValidationError):
        mapping_set.mapping_set_id = "https://example.org/replacement"  # ty: ignore[invalid-assignment]


def test_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "    unexpected: value\n")

    with pytest.raises(ConfigurationError, match="unexpected"):
        load_mapping_sets(config_path, root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [("mapping_file", "mapping.csv"), ("metadata_file", "mapping.metadata.json")],
)
def test_rejects_missing_mapping_files(tmp_path: Path, field: str, value: str) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace(f"{field}: {value}", f"{field}: missing.csv"))

    with pytest.raises(ConfigurationError, match="missing.csv"):
        load_mapping_sets(config_path, root=tmp_path)


def test_rejects_invalid_curie_namespace(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text().replace("test: https://example.org/", "test: relative/"))

    with pytest.raises(ConfigurationError, match="test"):
        load_mapping_sets(config_path, root=tmp_path)


def test_rejects_duplicate_mapping_set_keys(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    config_path.write_text(config_path.read_text() + config_path.read_text().split("mapping_sets:\n", maxsplit=1)[1])

    with pytest.raises(ConfigurationError, match="duplicate key: sample"):
        load_mapping_sets(config_path, root=tmp_path)


def test_unknown_mapping_set_lists_known_keys() -> None:
    config = load_mapping_sets(CONFIG_PATH, root=ROOT)

    with pytest.raises(ConfigurationError, match=r"Known mapping sets: omop-onz-g"):
        config.get("missing")


def test_paths_are_resolved_against_explicit_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = _write_config(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    mapping_set = load_mapping_sets(config_path, root=tmp_path).get("sample")

    assert mapping_set.mapping_file_path(tmp_path) == tmp_path / "mapping.csv"


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    (tmp_path / "mapping.csv").write_text("subject_id\n")
    (tmp_path / "mapping.metadata.json").write_text("{}")
    config_path = tmp_path / "mapping-sets.yaml"
    config_path.write_text(
        "mapping_sets:\n"
        "  sample:\n"
        "    mapping_set_id: https://example.org/mappings/sample\n"
        "    license: https://creativecommons.org/publicdomain/zero/1.0/\n"
        "    mapping_file: mapping.csv\n"
        "    metadata_file: mapping.metadata.json\n"
        "    curie_map:\n"
        "      test: https://example.org/\n"
        f"{extra}"
    )
    return config_path


def test_preserved_mapping_set_binds_subject_and_object_ontologies() -> None:
    mapping_set = load_mapping_sets(CONFIG_PATH, root=ROOT).get("omop-onz-g")

    assert mapping_set.ontologies is not None
    assert mapping_set.ontologies.subject == "omop-cdm"
    assert mapping_set.ontologies.object == "onz-g"


def test_mapping_set_without_a_binding_still_loads(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    assert load_mapping_sets(config_path, root=tmp_path).get("sample").ontologies is None


def test_binding_to_a_configured_ontology_source_is_accepted() -> None:
    ontology_sources = load_ontology_sources(ROOT / "registry/config/ontology-sources.yaml")

    config = load_mapping_sets(CONFIG_PATH, root=ROOT, ontology_sources=ontology_sources)

    assert config.get("omop-onz-g").ontologies is not None


def test_binding_to_an_unconfigured_ontology_source_fails_at_load_time(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "    ontologies:\n      subject: missing\n      object: missing\n")
    ontology_sources = load_ontology_sources(ROOT / "registry/config/ontology-sources.yaml")

    with pytest.raises(ConfigurationError, match=r"sample.*missing.*Known ontology sources"):
        load_mapping_sets(config_path, root=tmp_path, ontology_sources=ontology_sources)
