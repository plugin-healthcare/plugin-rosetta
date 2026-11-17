from pathlib import Path

import pytest

from plugin_rosetta.errors import ConfigurationError, RosettaIOError, ValidationError
from plugin_rosetta.mapping import api as mapping_api
from plugin_rosetta.mapping import build_mapping_artifacts, read_mapping_set

ROOT = Path(__file__).parents[2]


def test_preserved_mapping_set_resolves_against_both_bound_ontologies(ontology_cache: Path) -> None:
    result = read_mapping_set("omop-onz-g", root=ROOT, check_references=True, cache_dir=ontology_cache)

    assert result.mapping_set.mappings is not None
    assert len(result.mapping_set.mappings) == 8
    assert result.report.is_valid


def test_drifted_ontology_term_is_reported_once(drifted_ontology_cache: Path) -> None:
    result = read_mapping_set("omop-onz-g", root=ROOT, check_references=True, cache_dir=drifted_ontology_cache)

    unresolved = [issue for issue in result.report.issues if issue.code == "referential.unresolved"]

    assert not result.report.is_valid
    assert len(unresolved) == 1
    assert unresolved[0].location == "row 9, column subject_id"
    assert "omop:Vocabulary" in unresolved[0].message


def test_references_are_not_checked_unless_requested(tmp_path: Path) -> None:
    result = read_mapping_set("omop-onz-g", root=ROOT, cache_dir=tmp_path)

    assert result.report.is_valid


def test_empty_cache_instructs_the_curator_to_fetch(tmp_path: Path) -> None:
    with pytest.raises(RosettaIOError, match="rosetta ontology fetch omop-cdm"):
        read_mapping_set("omop-onz-g", root=ROOT, check_references=True, cache_dir=tmp_path)


def test_unbound_mapping_set_cannot_be_reference_checked(tmp_path: Path, ontology_cache: Path) -> None:
    config_path = _write_unbound_config(tmp_path)

    with pytest.raises(ConfigurationError, match="no ontology binding"):
        read_mapping_set(
            "sample",
            config_path=config_path,
            root=tmp_path,
            check_references=True,
            ontology_config_path=ROOT / "registry/config/ontology-sources.yaml",
            cache_dir=ontology_cache,
        )


def test_build_writes_nothing_when_a_reference_is_unresolved(tmp_path: Path, drifted_ontology_cache: Path) -> None:
    output_dir = tmp_path / "build"
    output_dir.mkdir()

    with pytest.raises(ValidationError, match="referential"):
        build_mapping_artifacts(
            "omop-onz-g",
            output_dir=output_dir,
            root=ROOT,
            check_references=True,
            cache_dir=drifted_ontology_cache,
        )

    assert list(output_dir.iterdir()) == []


def test_build_writes_artifacts_when_every_reference_resolves(tmp_path: Path, ontology_cache: Path) -> None:
    output_dir = tmp_path / "build"
    output_dir.mkdir()

    sssom_path, turtle_path = build_mapping_artifacts(
        "omop-onz-g",
        output_dir=output_dir,
        root=ROOT,
        check_references=True,
        cache_dir=ontology_cache,
    )

    assert sssom_path.is_file()
    assert turtle_path.is_file()


def test_build_renders_every_artifact_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "build"

    def fail_render(_mapping_set: object) -> str:
        raise ValidationError("unknown predicate prefix")

    monkeypatch.setattr(mapping_api, "render_turtle", fail_render)

    with pytest.raises(ValidationError, match="unknown predicate prefix"):
        build_mapping_artifacts("omop-onz-g", output_dir=output_dir, root=ROOT)

    assert not output_dir.exists()


def _write_unbound_config(tmp_path: Path) -> Path:
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
    )
    return config_path
