import io
import shutil
import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from plugin_rosetta import IssueSeverity, ValidationIssue, ValidationReport, cli
from plugin_rosetta.cli import app


def test_cli_displays_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Rosetta mapping toolbox" in result.stdout


def test_init_creates_empty_workspace_without_domain_specific_inputs(tmp_path: Path) -> None:
    destination = tmp_path / "workspace"

    result = CliRunner().invoke(app, ["init", str(destination)])

    assert result.exit_code == 0
    workspace = yaml.safe_load((destination / "rosetta.yaml").read_text())
    assert workspace["mapping_sets"] == []
    assert workspace["ontology_sources"] == []
    assert workspace["vocabulary_sources"] == []


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
        archive.writestr(
            "CONCEPT_RELATIONSHIP.csv",
            "concept_id_1\tconcept_id_2\trelationship_id\tinvalid_reason\n"
            'SYNTHETIC-1\tSYNTHETIC-2\tSynthetic relationship\t""\n',
        )
        archive.writestr(
            "RELATIONSHIP.csv",
            "relationship_id\trelationship_name\trelationship_concept_id\n"
            "Synthetic relationship\tSynthetic relationship\tSYNTHETIC-REL-1\n",
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
    assert "version is 'unversioned'" in result.stdout
    assert (cache_dir / "omop/unversioned/CONCEPT.csv").is_file()


def test_vocabulary_ingest_rejects_invalid_table_before_cache_promotion(tmp_path: Path) -> None:
    zip_path = tmp_path / "release.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CONCEPT.csv", "concept_id\nSYNTHETIC-1\n")
        archive.writestr(
            "CONCEPT_RELATIONSHIP.csv",
            "concept_id_1\tconcept_id_2\trelationship_id\tinvalid_reason\n"
            'SYNTHETIC-1\tSYNTHETIC-2\tSynthetic relationship\t""\n',
        )
        archive.writestr(
            "RELATIONSHIP.csv",
            "relationship_id\trelationship_name\trelationship_concept_id\n"
            "Synthetic relationship\tSynthetic relationship\tSYNTHETIC-REL-1\n",
        )
    zip_path.write_bytes(buffer.getvalue())
    cache_dir = tmp_path / "vocabularies"

    result = CliRunner().invoke(
        app,
        ["vocabulary", "ingest", "omop", str(zip_path), "--cache-dir", str(cache_dir)],
    )

    assert result.exit_code == 1
    assert "Missing expected columns" in result.output
    assert not (cache_dir / "omop/unversioned").exists()


def test_vocabulary_build_omop_writes_graph_and_sidecar(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vocabularies"
    release_dir = cache_dir / "omop/unversioned"
    shutil.copytree(
        Path(__file__).parent / "fixtures/vocabulary/athena",
        release_dir,
    )
    output_dir = tmp_path / "output"

    result = CliRunner().invoke(
        app,
        [
            "vocabulary",
            "build-omop",
            "--cache-dir",
            str(cache_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert str(output_dir / "omop.ttl") in result.stdout
    assert str(output_dir / "omop.meta.json") in result.stdout
    assert (output_dir / "omop.ttl").is_file()
    assert (output_dir / "omop.meta.json").is_file()


@pytest.mark.parametrize(
    ("command", "filename"),
    [
        ("build-dhd-diagnosethesaurus", "dhd-diagnosethesaurus.ttl"),
        ("build-dhd-verrichtingenthesaurus", "dhd-verrichtingenthesaurus.ttl"),
    ],
)
def test_vocabulary_build_dhd_commands_write_graph_and_sidecar(
    tmp_path: Path,
    command: str,
    filename: str,
) -> None:
    cache_dir = tmp_path / "vocabularies"
    shutil.copytree(
        Path(__file__).parent / "fixtures/vocabulary/dhd",
        cache_dir / "dhd-thesauri/202508",
    )
    output_dir = tmp_path / "output"

    result = CliRunner().invoke(
        app,
        [
            "vocabulary",
            command,
            "--as-of",
            "20260910",
            "--cache-dir",
            str(cache_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert str(output_dir / filename) in result.stdout
    assert str(output_dir / filename.replace(".ttl", ".meta.json")) in result.stdout


@pytest.mark.parametrize(
    ("source_name", "command", "filename"),
    [
        ("loinc-snomed", "build-loinc-snomed", "loinc-snomed.ttl"),
        ("snomed-international", "build-snomed-international", "snomed-international.ttl"),
    ],
)
def test_vocabulary_build_rf2_commands_write_graph_and_sidecar(
    tmp_path: Path,
    source_name: str,
    command: str,
    filename: str,
) -> None:
    cache_dir = tmp_path / "vocabularies"
    version = "2.82" if source_name == "loinc-snomed" else "20260101"
    shutil.copytree(
        Path(__file__).parent / "fixtures/vocabulary/rf2",
        cache_dir / source_name / version,
    )
    output_dir = tmp_path / "output"

    result = CliRunner().invoke(
        app,
        [
            "vocabulary",
            command,
            "--cache-dir",
            str(cache_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / filename).is_file()
    assert (output_dir / filename.replace(".ttl", ".meta.json")).is_file()


def test_vocabulary_merge_command_requires_every_registered_graph(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["vocabulary", "merge", "--output-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "Missing vocabulary graph inputs" in result.output


def test_vocabulary_merge_command_writes_combined_graph(tmp_path: Path) -> None:
    for filename in (
        "omop.ttl",
        "dhd-diagnosethesaurus.ttl",
        "dhd-verrichtingenthesaurus.ttl",
        "loinc-snomed.ttl",
        "snomed-international.ttl",
    ):
        (tmp_path / filename).write_text(
            f"<https://example.org/{filename}> <https://example.org/p> <https://example.org/o> .\n"
        )

    result = CliRunner().invoke(app, ["vocabulary", "merge", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "vocabularies.ttl").is_file()


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
