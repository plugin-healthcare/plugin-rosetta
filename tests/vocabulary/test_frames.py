from pathlib import Path

import polars as pl
import pytest

from plugin_rosetta.core.report import IssueSeverity
from plugin_rosetta.vocabulary.frames import load_table_contract, validate_release_frame

ROOT = Path(__file__).parents[2]
CONTRACT_PATH = ROOT / "registry/schemas/vocabularies/dhd-thesaurus-concept.yaml"


def test_valid_release_frame_passes_declared_contract() -> None:
    contract = load_table_contract(CONTRACT_PATH)
    frame = pl.DataFrame(
        {
            "ConceptID": ["SYNTHETIC-1"],
            "Begindatum": ["20260101"],
            "Einddatum": [None],
        },
        schema={"ConceptID": pl.String, "Begindatum": pl.String, "Einddatum": pl.String},
    )

    report = validate_release_frame(frame, contract, source_path=Path("synthetic.csv"))

    assert report.is_valid
    assert report.issues == ()


def test_missing_columns_are_reported_together() -> None:
    contract = load_table_contract(CONTRACT_PATH)
    frame = pl.DataFrame({"ConceptID": ["SYNTHETIC-1"]})

    report = validate_release_frame(frame, contract, source_path=Path("synthetic.csv"))

    assert not report.is_valid
    assert len(report.issues) == 1
    assert report.issues[0].severity is IssueSeverity.ERROR
    assert "Begindatum" in report.issues[0].message
    assert "Einddatum" in report.issues[0].message
    assert report.issues[0].location == "synthetic.csv"


def test_extra_columns_are_informational() -> None:
    contract = load_table_contract(CONTRACT_PATH)
    frame = pl.DataFrame(
        {
            "ConceptID": ["SYNTHETIC-1"],
            "Begindatum": ["20260101"],
            "Einddatum": [None],
            "FutureColumn": ["allowed"],
        },
        schema={
            "ConceptID": pl.String,
            "Begindatum": pl.String,
            "Einddatum": pl.String,
            "FutureColumn": pl.String,
        },
    )

    report = validate_release_frame(frame, contract, source_path=Path("synthetic.csv"))

    assert report.is_valid
    assert report.issues[0].severity is IssueSeverity.INFO
    assert "FutureColumn" in report.issues[0].message


def test_non_nullable_column_reports_null_content() -> None:
    contract = load_table_contract(CONTRACT_PATH)
    frame = pl.DataFrame(
        {
            "ConceptID": [None],
            "Begindatum": ["20260101"],
            "Einddatum": [None],
        },
        schema={"ConceptID": pl.String, "Begindatum": pl.String, "Einddatum": pl.String},
    )

    report = validate_release_frame(frame, contract, source_path=Path("synthetic.csv"))

    assert not report.is_valid
    assert report.issues[0].code == "vocabulary.null-value"
    assert "ConceptID" in report.issues[0].message


@pytest.mark.parametrize(
    ("fixture_path", "contract_path", "separator"),
    [
        (
            "tests/fixtures/vocabulary/athena/CONCEPT.csv",
            "registry/schemas/vocabularies/omop-concept.yaml",
            "\t",
        ),
        (
            "tests/fixtures/vocabulary/dhd/thesauri/DT/202609_uitleverformaat4.3/SYN_ThesaurusConcept.csv",
            "registry/schemas/vocabularies/dhd-thesaurus-concept.yaml",
            ",",
        ),
        (
            "tests/fixtures/vocabulary/rf2/Snapshot/Terminology/sct2_Concept_Snapshot_SYNTHETIC_20260101.txt",
            "registry/schemas/vocabularies/rf2-concept.yaml",
            "\t",
        ),
    ],
)
def test_synthetic_release_tables_satisfy_their_contracts(
    fixture_path: str,
    contract_path: str,
    separator: str,
) -> None:
    path = ROOT / fixture_path
    frame = pl.read_csv(path, separator=separator, infer_schema=False)

    report = validate_release_frame(
        frame,
        load_table_contract(ROOT / contract_path),
        source_path=path,
    )

    assert report.is_valid
