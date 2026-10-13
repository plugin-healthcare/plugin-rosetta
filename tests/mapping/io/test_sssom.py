from pathlib import Path

import pytest
from linkml_runtime.utils.metamodelcore import URI
from sssom import parse_sssom_table

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.mapping import read_mapping_set
from plugin_rosetta.mapping.io.sssom import read_sssom_tsv, write_sssom_tsv
from plugin_rosetta.mapping.models.sssom import Mapping, MappingSet

ROOT = Path(__file__).parents[3]


def test_writes_deterministic_standard_sssom_tsv(tmp_path: Path) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=ROOT).mapping_set
    first_path = tmp_path / "first.sssom.tsv"
    second_path = tmp_path / "nested/second.sssom.tsv"

    write_sssom_tsv(mapping_set, first_path)
    write_sssom_tsv(mapping_set, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    lines = first_path.read_text().splitlines()
    assert lines[0].startswith("# ")
    assert sum(not line.startswith("# ") for line in lines) == 9
    assert "orcid:0000-0001-8979-9194" in first_path.read_text()
    assert "['orcid:" not in first_path.read_text()


def test_sssom_py_reads_written_output(tmp_path: Path) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=ROOT).mapping_set
    output_path = tmp_path / "mapping.sssom.tsv"
    write_sssom_tsv(mapping_set, output_path)

    parsed = parse_sssom_table(output_path)

    assert len(parsed.df) == 8
    assert parsed.metadata["mapping_set_id"] == str(mapping_set.mapping_set_id)


def test_round_trip_restores_multivalued_fields(tmp_path: Path) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=ROOT).mapping_set
    output_path = tmp_path / "mapping.sssom.tsv"
    write_sssom_tsv(mapping_set, output_path)

    restored = read_sssom_tsv(output_path)

    assert restored.mappings is not None
    assert mapping_set.mappings is not None
    assert len(restored.mappings) == 8
    assert restored.mappings[0].author_id == ["orcid:0000-0001-8979-9194"]
    assert restored.mappings[0].reviewer_id == []
    assert restored.mappings[0].comment == mapping_set.mappings[0].comment


def _mapping_set(mappings: list[Mapping]) -> MappingSet:
    return MappingSet(
        mapping_set_id=URI("https://example.org/set"),
        license=URI("https://example.org/license"),
        curie_map={"ex": "https://example.org/"},
        mappings=mappings,
    )


def test_round_trip_keeps_line_breaks_in_quoted_comment(tmp_path: Path) -> None:
    mapping = Mapping(
        subject_id="ex:a",
        predicate_id="skos:exactMatch",
        object_id="ex:b",
        mapping_justification="semapv:ManualMappingCuration",
        comment="first line\nsecond line",
    )
    output_path = tmp_path / "mapping.sssom.tsv"
    write_sssom_tsv(_mapping_set([mapping]), output_path)

    restored = read_sssom_tsv(output_path)

    assert restored.mappings is not None
    assert restored.mappings[0].comment == "first line\nsecond line"


def test_empty_mapping_set_is_written_with_a_header_row(tmp_path: Path) -> None:
    output_path = tmp_path / "empty.sssom.tsv"

    write_sssom_tsv(_mapping_set([]), output_path)

    table_lines = [line for line in output_path.read_text().splitlines() if not line.startswith("#")]
    assert table_lines == ["subject_id\tpredicate_id\tobject_id\tmapping_justification"]
    assert read_sssom_tsv(output_path).mappings == []


def test_unknown_column_is_reported_as_validation_error(tmp_path: Path) -> None:
    source = tmp_path / "unknown.sssom.tsv"
    source.write_text(
        "# mapping_set_id: https://example.org/set\n"
        "# license: https://example.org/license\n"
        "subject_id\tpredicate_id\tobject_id\tmapping_justification\tfoo\n"
        "ex:a\tskos:exactMatch\tex:b\tsemapv:ManualMappingCuration\tbar\n"
    )

    with pytest.raises(ValidationError, match="foo"):
        read_sssom_tsv(source)
