import io
import zipfile
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from plugin_rosetta import cli
from plugin_rosetta.cli import app
from plugin_rosetta.core.report import IssueSeverity, ValidationIssue, ValidationReport

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_displays_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Rosetta mapping toolbox" in result.stdout


def test_mapping_list_displays_configured_mapping_sets() -> None:
    result = CliRunner().invoke(app, ["mapping", "list"])

    assert result.exit_code == 0
    assert "omop-onz-g" in result.stdout
    assert "registry/mappings/omop-onz-g.csv" in result.stdout


def test_mapping_validate_reports_conforming_rows() -> None:
    result = CliRunner().invoke(app, ["mapping", "validate", "omop-onz-g"])

    assert result.exit_code == 0
    assert "8 conforming rows" in result.stdout


def test_mapping_build_and_report_write_open_artifacts(tmp_path: Path) -> None:
    build_result = CliRunner().invoke(
        app,
        ["mapping", "build", "omop-onz-g", "--output-dir", str(tmp_path)],
    )
    report_result = CliRunner().invoke(
        app,
        ["mapping", "report", "omop-onz-g", "--output-dir", str(tmp_path)],
    )

    assert build_result.exit_code == 0
    assert report_result.exit_code == 0
    assert (tmp_path / "omop-onz-g.sssom.tsv").is_file()
    assert (tmp_path / "omop-onz-g.ttl").is_file()
    assert (tmp_path / "omop-onz-g.md").is_file()
    assert (tmp_path / "omop-onz-g.html").is_file()


def test_ontology_fetch_writes_path_and_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cached_path = tmp_path / "ontology.ttl"
    warning = ValidationIssue(
        code="ontology.missing-checksum",
        severity=IssueSeverity.WARNING,
        location="sample",
        message="No checksum pinned for 'sample'; computed SHA-256 deadbeef.",
    )

    def fake_fetch_ontology_source(
        name: str,
        *,
        config_path: Path,
        cache_dir: Path,
        force: bool,
    ) -> tuple[Path, ValidationReport]:
        assert name == "sample"
        assert force is False
        assert config_path.name == "ontology-sources.yaml"
        assert cache_dir.name == "ontologies"
        return cached_path, ValidationReport(issues=(warning,))

    monkeypatch.setattr(cli, "fetch_ontology_source", fake_fetch_ontology_source)

    result = CliRunner().invoke(app, ["ontology", "fetch", "sample"])

    assert result.exit_code == 0
    assert str(cached_path) in result.stdout
    assert "No checksum pinned" in result.stdout


def test_vocabulary_ingest_writes_path_and_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cached_path = tmp_path / "vocabularies/sample/1.0"
    warning = ValidationIssue(
        code="vocabulary.missing-checksum",
        severity=IssueSeverity.WARNING,
        location="sample",
        message="No checksum pinned for vocabulary source 'sample'; computed SHA-256 deadbeef.",
    )

    def fake_ingest_release(
        name: str,
        zip_path: Path,
        *,
        config_path: Path,
        cache_dir: Path,
        force: bool,
    ) -> tuple[Path, ValidationReport]:
        assert name == "sample"
        assert zip_path.name == "release.zip"
        assert force is False
        assert config_path.name == "vocabulary-sources.yaml"
        assert cache_dir.name == "vocabularies"
        return cached_path, ValidationReport(issues=(warning,))

    monkeypatch.setattr(cli, "ingest_release", fake_ingest_release)

    result = CliRunner().invoke(app, ["vocabulary", "ingest", "sample", "release.zip"])

    assert result.exit_code == 0
    assert str(cached_path) in result.stdout
    assert "No checksum pinned" in result.stdout


def test_vocabulary_ingest_command_extracts_synthetic_release(tmp_path: Path) -> None:
    zip_path = tmp_path / "release.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "CONCEPT.csv",
            (
                "concept_id\tconcept_name\tdomain_id\tvocabulary_id\tconcept_class_id\tstandard_concept\t"
                "concept_code\tvalid_start_date\tvalid_end_date\tinvalid_reason\n"
                "SYNTHETIC-1\tSynthetic concept\tCondition\tSYNTHETIC\tClass\tS\tCODE-1\t"
                '20260101\t20991231\t""\n'
            ),
        )
    zip_path.write_bytes(buffer.getvalue())
    cache_dir = tmp_path / "vocabularies"

    result = CliRunner().invoke(
        app,
        ["vocabulary", "ingest", "omop", str(zip_path), "--cache-dir", str(cache_dir)],
    )

    assert result.exit_code == 0
    assert str(cache_dir / "omop/unversioned") in result.stdout
    assert "computed SHA-256" in result.stdout
    assert (cache_dir / "omop/unversioned/CONCEPT.csv").is_file()


def test_vocabulary_ingest_rejects_invalid_table_before_cache_promotion(tmp_path: Path) -> None:
    zip_path = tmp_path / "release.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CONCEPT.csv", "concept_id\nSYNTHETIC-1\n")
    zip_path.write_bytes(buffer.getvalue())
    cache_dir = tmp_path / "vocabularies"

    result = CliRunner().invoke(
        app,
        ["vocabulary", "ingest", "omop", str(zip_path), "--cache-dir", str(cache_dir)],
    )

    assert result.exit_code == 1
    assert "Missing expected columns" in result.output
    assert not (cache_dir / "omop/unversioned").exists()


def test_mapping_validate_with_check_references_succeeds(ontology_cache: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["mapping", "validate", "omop-onz-g", "--check-references", "--cache-dir", str(ontology_cache)],
    )

    assert result.exit_code == 0
    assert "8 conforming rows" in result.stdout


def test_mapping_validate_exits_non_zero_and_prints_every_referential_issue(
    drifted_ontology_cache: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["mapping", "validate", "omop-onz-g", "--check-references", "--cache-dir", str(drifted_ontology_cache)],
    )

    assert result.exit_code == 1
    assert "row 9, column subject_id" in result.stdout
    assert "omop:Vocabulary" in result.stdout


def test_mapping_build_refuses_to_write_when_a_reference_is_unresolved(
    tmp_path: Path,
    drifted_ontology_cache: Path,
) -> None:
    output_dir = tmp_path / "build"
    output_dir.mkdir()

    result = CliRunner().invoke(
        app,
        [
            "mapping",
            "build",
            "omop-onz-g",
            "--output-dir",
            str(output_dir),
            "--check-references",
            "--cache-dir",
            str(drifted_ontology_cache),
        ],
    )

    assert result.exit_code != 0
    assert list(output_dir.iterdir()) == []


def test_mapping_validate_reports_an_empty_cache_without_a_traceback(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["mapping", "validate", "omop-onz-g", "--check-references", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "rosetta ontology fetch omop-cdm" in result.output
