import json
from pathlib import Path  # noqa: TC003

from typer.testing import CliRunner

from plugin_rosetta.cli import app


def test_artifact_register_list_and_diff_print_json(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    artifact = tmp_path / "value.txt"
    artifact.write_text("first")
    runner = CliRunner()

    first = runner.invoke(
        app,
        [
            "artifact",
            "register",
            "example",
            str(artifact),
            "--kind",
            "text",
            "--source-name",
            "example",
            "--source-version",
            "1",
            "--catalog-dir",
            str(catalog),
        ],
    )
    artifact.write_text("second")
    second = runner.invoke(
        app,
        [
            "artifact",
            "register",
            "example",
            str(artifact),
            "--kind",
            "text",
            "--source-name",
            "example",
            "--source-version",
            "2",
            "--catalog-dir",
            str(catalog),
        ],
    )
    listed = runner.invoke(
        app,
        ["artifact", "list", "example", "--catalog-dir", str(catalog)],
    )
    difference = runner.invoke(
        app,
        [
            "artifact",
            "diff",
            "example",
            json.loads(first.stdout)["version"],
            json.loads(second.stdout)["version"],
            "--catalog-dir",
            str(catalog),
        ],
    )

    assert first.exit_code == second.exit_code == listed.exit_code == difference.exit_code == 0
    assert len(json.loads(listed.stdout)) == 2
    assert json.loads(difference.stdout)["checksum_changed"]
