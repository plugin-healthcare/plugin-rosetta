from typing import TYPE_CHECKING

from typer.testing import CliRunner

from plugin_rosetta.cli import app

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
