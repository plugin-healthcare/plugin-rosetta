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
