import json
from pathlib import Path  # noqa: TC003

import pytest

from plugin_rosetta.artifacts import (
    ArtifactInput,
    ArtifactKind,
    dependents,
    list_versions,
    register_artifact,
    resolve_artifact,
)
from plugin_rosetta.errors import ArtifactError


def test_register_is_content_addressed_idempotent_and_plain_json(tmp_path: Path) -> None:
    artifact = tmp_path / "graph.ttl"
    artifact.write_text("@prefix ex: <https://example.org/> . ex:a ex:p ex:b .\n")

    first = register_artifact(
        "example-graph",
        artifact,
        ArtifactKind.RDF,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="1",
        inputs=(ArtifactInput(name="source", version="1", checksum="abc"),),
    )
    second = register_artifact(
        "example-graph",
        artifact,
        ArtifactKind.RDF,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="1",
        inputs=(ArtifactInput(name="source", version="1", checksum="abc"),),
    )

    assert first.version == second.version
    assert len(list_versions("example-graph", catalog_dir=tmp_path / "catalog")) == 1
    resolved = resolve_artifact("example-graph", first.version, catalog_dir=tmp_path / "catalog")
    manifest = json.loads(resolved.manifest_path.read_text())
    assert manifest["kind"] == "rdf"
    assert manifest["source_name"] == "example"
    assert manifest["source_version"] == "1"
    assert manifest["inputs"][0]["checksum"] == "abc"
    assert manifest["tool_version"] == "0.1.0"
    assert manifest["built_at"].endswith("+00:00")


def test_list_versions_is_stably_ordered(tmp_path: Path) -> None:
    artifact = tmp_path / "table.csv"
    artifact.write_text("id,value\n1,a\n")
    first = register_artifact(
        "example-table",
        artifact,
        ArtifactKind.TABLE,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="1",
        key_columns=("id",),
    )
    artifact.write_text("id,value\n1,b\n")
    second = register_artifact(
        "example-table",
        artifact,
        ArtifactKind.TABLE,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="2",
        key_columns=("id",),
    )

    assert [item.version for item in list_versions("example-table", catalog_dir=tmp_path / "catalog")] == [
        first.version,
        second.version,
    ]


def test_unknown_artifact_names_known_artifacts(tmp_path: Path) -> None:
    artifact = tmp_path / "value.txt"
    artifact.write_text("value")
    register_artifact(
        "known",
        artifact,
        ArtifactKind.TEXT,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="1",
    )

    with pytest.raises(ArtifactError, match="missing.*known"):
        resolve_artifact("missing", "unknown", catalog_dir=tmp_path / "catalog")


def test_dependents_find_manifests_that_name_changed_input(tmp_path: Path) -> None:
    artifact = tmp_path / "value.txt"
    artifact.write_text("value")
    registered = register_artifact(
        "dependent",
        artifact,
        ArtifactKind.TEXT,
        catalog_dir=tmp_path / "catalog",
        source_name="derived",
        source_version="1",
        inputs=(ArtifactInput(name="snomed-international", version="20260101", checksum="abc"),),
    )

    assert dependents("snomed-international", catalog_dir=tmp_path / "catalog") == (registered.manifest,)


def test_reregistering_content_with_different_provenance_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "value.txt"
    artifact.write_text("value")
    register_artifact(
        "example",
        artifact,
        ArtifactKind.TEXT,
        catalog_dir=tmp_path / "catalog",
        source_name="example",
        source_version="1",
    )

    with pytest.raises(ArtifactError, match="different provenance"):
        register_artifact(
            "example",
            artifact,
            ArtifactKind.TEXT,
            catalog_dir=tmp_path / "catalog",
            source_name="example",
            source_version="2",
        )
