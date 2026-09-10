from pathlib import Path  # noqa: TC003

import pytest

from plugin_rosetta.artifacts import ArtifactKind, diff_artifacts, register_artifact
from plugin_rosetta.errors import ArtifactError


def _register(
    tmp_path: Path,
    name: str,
    version: str,
    content: str,
    kind: ArtifactKind,
    *,
    key_columns: tuple[str, ...] = (),
) -> str:
    artifact = tmp_path / f"{version}.txt"
    artifact.write_text(content)
    return register_artifact(
        name,
        artifact,
        kind,
        catalog_dir=tmp_path / "catalog",
        source_name=name,
        source_version=version,
        key_columns=key_columns,
    ).version


def test_table_diff_stops_at_incompatible_schema(tmp_path: Path) -> None:
    base = _register(tmp_path, "table", "1", "id,value\n1,1\n", ArtifactKind.TABLE, key_columns=("id",))
    head = _register(tmp_path, "table", "2", "id,label\n1,one\n", ArtifactKind.TABLE, key_columns=("id",))

    difference = diff_artifacts("table", base, head, catalog_dir=tmp_path / "catalog")

    assert difference.checksum_changed
    assert difference.schema_difference is not None
    assert difference.schema_difference.added == ("label",)
    assert difference.schema_difference.removed == ("value",)
    assert difference.rows is None


def test_table_diff_reports_keyed_added_removed_and_changed_rows(tmp_path: Path) -> None:
    base = _register(
        tmp_path,
        "table",
        "1",
        "id,value\n1,old\n2,removed\n",
        ArtifactKind.TABLE,
        key_columns=("id",),
    )
    head = _register(
        tmp_path,
        "table",
        "2",
        "id,value\n1,new\n3,added\n",
        ArtifactKind.TABLE,
        key_columns=("id",),
    )

    rows = diff_artifacts("table", base, head, catalog_dir=tmp_path / "catalog").rows

    assert rows is not None
    assert rows.added == (("3",),)
    assert rows.removed == (("2",),)
    assert rows.changed == (("1",),)


def test_table_diff_reports_retyped_columns_before_rows(tmp_path: Path) -> None:
    base = _register(tmp_path, "table", "1", "id,value\n1,10\n", ArtifactKind.TABLE, key_columns=("id",))
    head = _register(tmp_path, "table", "2", "id,value\n1,ten\n", ArtifactKind.TABLE, key_columns=("id",))

    difference = diff_artifacts("table", base, head, catalog_dir=tmp_path / "catalog")

    assert difference.schema_difference is not None
    assert difference.schema_difference.retyped == ("value",)
    assert difference.rows is None


def test_keyed_diff_rejects_duplicate_keys_instead_of_hiding_rows(tmp_path: Path) -> None:
    base = _register(
        tmp_path,
        "table",
        "1",
        "id,value\n1,first\n1,second\n",
        ArtifactKind.TABLE,
        key_columns=("id",),
    )
    head = _register(
        tmp_path,
        "table",
        "2",
        "id,value\n1,second\n",
        ArtifactKind.TABLE,
        key_columns=("id",),
    )

    with pytest.raises(ArtifactError, match="Duplicate artifact row key"):
        diff_artifacts("table", base, head, catalog_dir=tmp_path / "catalog")


def test_table_diff_rejects_changed_key_contracts(tmp_path: Path) -> None:
    base = _register(
        tmp_path,
        "table",
        "1",
        "id,code,value\n1,a,old\n",
        ArtifactKind.TABLE,
        key_columns=("id",),
    )
    head = _register(
        tmp_path,
        "table",
        "2",
        "id,code,value\n1,a,new\n",
        ArtifactKind.TABLE,
        key_columns=("code",),
    )

    with pytest.raises(ArtifactError, match="different key columns"):
        diff_artifacts("table", base, head, catalog_dir=tmp_path / "catalog")


def test_sssom_diff_uses_mapping_identity_and_reports_metadata_change(tmp_path: Path) -> None:
    header = "subject_id\tpredicate_id\tobject_id\tconfidence\n"
    base = _register(
        tmp_path,
        "mapping",
        "1",
        header + "A\tskos:exactMatch\tB\t0.8\n",
        ArtifactKind.SSSOM,
    )
    head = _register(
        tmp_path,
        "mapping",
        "2",
        header + "A\tskos:exactMatch\tB\t0.9\n",
        ArtifactKind.SSSOM,
    )

    mappings = diff_artifacts("mapping", base, head, catalog_dir=tmp_path / "catalog").mappings

    assert mappings is not None
    assert mappings.changed == (("A", "skos:exactMatch", "B"),)


def test_rdf_diff_is_semantic_and_deterministic_for_blank_nodes(tmp_path: Path) -> None:
    base = _register(
        tmp_path,
        "graph",
        "1",
        '@prefix ex: <https://example.org/> . [] ex:value "old" .',
        ArtifactKind.RDF,
    )
    head = _register(
        tmp_path,
        "graph",
        "2",
        '@prefix ex: <https://example.org/> . [] ex:value "new" .',
        ArtifactKind.RDF,
    )

    first = diff_artifacts("graph", base, head, catalog_dir=tmp_path / "catalog").triples
    second = diff_artifacts("graph", base, head, catalog_dir=tmp_path / "catalog").triples

    assert first == second
    assert first is not None
    assert len(first.added) == 1
    assert len(first.removed) == 1
