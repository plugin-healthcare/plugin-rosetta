import json
from pathlib import Path

import pytest

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.utils.io.csvw import read_mapping_rows

ROOT = Path(__file__).parents[3]
CSV_PATH = ROOT / "registry/mappings/omop-onz-g.csv"
METADATA_PATH = ROOT / "registry/mappings/omop-onz-g.metadata.json"


def test_reads_csvw_datatypes_and_multivalued_fields() -> None:
    result = read_mapping_rows(CSV_PATH, METADATA_PATH)

    assert len(result.rows) == 8
    assert result.rows[0]["confidence"] == 0.9
    assert result.rows[0]["author_id"] == ["orcid:0000-0001-8979-9194"]
    assert result.rows[0]["reviewer_id"] == []
    assert result.report.issues[0].code == "csvw.empty-cell"


def test_rejects_header_that_does_not_match_metadata(tmp_path: Path) -> None:
    csv_path, metadata_path = _write_table(tmp_path, "wrong_header\nvalue\n")

    with pytest.raises(ValidationError, match="CSVW"):
        read_mapping_rows(csv_path, metadata_path)


def test_rejects_duplicate_primary_key(tmp_path: Path) -> None:
    csv_path, metadata_path = _write_table(
        tmp_path,
        "subject_id,predicate_id,object_id\ntest:a,test:predicate,test:b\ntest:a,test:predicate,test:b\n",
    )

    with pytest.raises(ValidationError, match="duplicate primary key"):
        read_mapping_rows(csv_path, metadata_path)


def _write_table(tmp_path: Path, content: str) -> tuple[Path, Path]:
    csv_path = tmp_path / "mapping.csv"
    csv_path.write_text(content)
    metadata_path = tmp_path / "mapping.metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "@context": "http://www.w3.org/ns/csvw",
                "url": "mapping.csv",
                "tableSchema": {
                    "columns": [
                        {"name": "subject_id", "datatype": "string", "required": True},
                        {"name": "predicate_id", "datatype": "string", "required": True},
                        {"name": "object_id", "datatype": "string", "required": True},
                    ],
                    "primaryKey": ["subject_id", "predicate_id", "object_id"],
                },
            }
        )
    )
    return csv_path, metadata_path
