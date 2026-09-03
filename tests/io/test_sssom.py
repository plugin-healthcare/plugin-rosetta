from pathlib import Path

from sssom import parse_sssom_table

from plugin_rosetta.application.mapping import read_mapping_set
from plugin_rosetta.io.sssom import read_sssom_tsv, write_sssom_tsv

ROOT = Path(__file__).parents[2]


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
