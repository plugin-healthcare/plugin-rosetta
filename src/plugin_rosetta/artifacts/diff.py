"""Typed differences between registered artifact versions."""

import csv
import io
from pathlib import Path  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict
from rdflib import Graph
from rdflib.compare import to_canonical_graph

from plugin_rosetta.artifacts.catalog import DEFAULT_ARTIFACT_CATALOG, resolve_artifact
from plugin_rosetta.artifacts.identity import ArtifactKind
from plugin_rosetta.errors import ArtifactError

type RowKey = tuple[str, ...]


class SchemaDifference(BaseModel):
    """Column-level differences that prevent a keyed row comparison."""

    model_config = ConfigDict(frozen=True)

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    retyped: tuple[str, ...] = ()


class KeyedDifference(BaseModel):
    """Added, removed, and changed records identified by stable keys."""

    model_config = ConfigDict(frozen=True)

    added: tuple[RowKey, ...] = ()
    removed: tuple[RowKey, ...] = ()
    changed: tuple[RowKey, ...] = ()


class TripleDifference(BaseModel):
    """Canonical N-Triples added to and removed from an RDF graph."""

    model_config = ConfigDict(frozen=True)

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


class ArtifactDifference(BaseModel):
    """Kind-aware difference between two registered artifacts."""

    model_config = ConfigDict(frozen=True)

    name: str
    base_version: str
    head_version: str
    checksum_changed: bool
    schema_difference: SchemaDifference | None = None
    rows: KeyedDifference | None = None
    mappings: KeyedDifference | None = None
    triples: TripleDifference | None = None


def _read_rows(content: str, delimiter: str) -> list[dict[str, str]]:
    lines = [line for line in content.splitlines() if line and not line.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter))


def _value_type(values: list[str]) -> str:
    nonempty = [value for value in values if value]
    if not nonempty:
        return "null"
    try:
        for value in nonempty:
            int(value)
    except ValueError:
        try:
            for value in nonempty:
                float(value)
        except ValueError:
            return "string"
        return "float"
    return "integer"


def _schema(rows: list[dict[str, str]]) -> dict[str, str]:
    if not rows:
        return {}
    return {column: _value_type([row[column] for row in rows]) for column in rows[0]}


def _keyed_difference(
    base_rows: list[dict[str, str]],
    head_rows: list[dict[str, str]],
    key_columns: tuple[str, ...],
) -> KeyedDifference:
    if not key_columns:
        raise ArtifactError("Keyed row differences require declared key columns")
    base = _rows_by_key(base_rows, key_columns)
    head = _rows_by_key(head_rows, key_columns)
    shared = base.keys() & head.keys()
    return KeyedDifference(
        added=tuple(sorted(head.keys() - base.keys())),
        removed=tuple(sorted(base.keys() - head.keys())),
        changed=tuple(sorted(key for key in shared if base[key] != head[key])),
    )


def _rows_by_key(rows: list[dict[str, str]], key_columns: tuple[str, ...]) -> dict[RowKey, dict[str, str]]:
    keyed: dict[RowKey, dict[str, str]] = {}
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        if key in keyed:
            raise ArtifactError(f"Duplicate artifact row key: {key!r}")
        keyed[key] = row
    return keyed


def _triple_lines(content: str) -> set[str]:
    graph = Graph().parse(data=content, format="turtle")
    serialized = to_canonical_graph(graph).serialize(format="nt")
    return set(serialized.splitlines())


def diff_artifacts(
    name: str,
    base_version: str,
    head_version: str,
    *,
    catalog_dir: Path = DEFAULT_ARTIFACT_CATALOG,
) -> ArtifactDifference:
    """Compare two versions, parsing only when their checksums differ."""
    base = resolve_artifact(name, base_version, catalog_dir=catalog_dir)
    head = resolve_artifact(name, head_version, catalog_dir=catalog_dir)
    changed = base_version != head_version
    common: dict[str, Any] = {
        "name": name,
        "base_version": base_version,
        "head_version": head_version,
        "checksum_changed": changed,
    }
    if not changed:
        return ArtifactDifference(**common)
    if base.manifest.kind is not head.manifest.kind:
        raise ArtifactError("Artifact versions of different kinds cannot be compared")

    base_text = base.artifact_path.read_text()
    head_text = head.artifact_path.read_text()
    kind = base.manifest.kind
    if kind is ArtifactKind.RDF:
        base_triples = _triple_lines(base_text)
        head_triples = _triple_lines(head_text)
        return ArtifactDifference(
            **common,
            triples=TripleDifference(
                added=tuple(sorted(head_triples - base_triples)),
                removed=tuple(sorted(base_triples - head_triples)),
            ),
        )
    if kind in {ArtifactKind.TABLE, ArtifactKind.SSSOM}:
        delimiter = "\t" if kind is ArtifactKind.SSSOM else ","
        base_rows = _read_rows(base_text, delimiter)
        head_rows = _read_rows(head_text, delimiter)
        base_schema = _schema(base_rows)
        head_schema = _schema(head_rows)
        schema = SchemaDifference(
            added=tuple(sorted(head_schema.keys() - base_schema.keys())),
            removed=tuple(sorted(base_schema.keys() - head_schema.keys())),
            retyped=tuple(
                sorted(
                    column
                    for column in base_schema.keys() & head_schema.keys()
                    if base_schema[column] != head_schema[column]
                )
            ),
        )
        if schema.added or schema.removed or schema.retyped:
            return ArtifactDifference(**common, schema_difference=schema)
        if kind is ArtifactKind.TABLE and base.manifest.key_columns != head.manifest.key_columns:
            raise ArtifactError(
                "Table artifact versions declare different key columns: "
                f"{base.manifest.key_columns!r} != {head.manifest.key_columns!r}"
            )
        keys = ("subject_id", "predicate_id", "object_id") if kind is ArtifactKind.SSSOM else base.manifest.key_columns
        difference = _keyed_difference(base_rows, head_rows, keys)
        field = "mappings" if kind is ArtifactKind.SSSOM else "rows"
        return ArtifactDifference(**common, **{field: difference})
    return ArtifactDifference(**common)
