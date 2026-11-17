from datetime import date

import pytest
import yaml

from plugin_rosetta.artifacts.identity import ArtifactKind, canonical_bytes, content_version
from plugin_rosetta.errors import ArtifactError


def test_text_identity_normalizes_line_endings_trailing_space_and_final_newline() -> None:
    first = content_version(ArtifactKind.TEXT, b"one  \r\ntwo\r\n")
    second = content_version(ArtifactKind.TEXT, b"one\ntwo\n\n")

    assert first == second


def test_rdf_identity_uses_canonical_triples_including_blank_nodes() -> None:
    first = b'@prefix ex: <https://example.org/> . [] ex:value "x" .'
    second = b'@prefix other: <https://example.org/> . _:different other:value "x" .'

    assert content_version(ArtifactKind.RDF, first) == content_version(ArtifactKind.RDF, second)


def test_identical_bytes_of_different_kinds_have_distinct_versions() -> None:
    assert content_version(ArtifactKind.TEXT, b"value") != content_version(ArtifactKind.TABLE, b"value")


def test_invalid_rdf_fails_as_an_artifact_error() -> None:
    with pytest.raises(ArtifactError, match="Cannot parse RDF artifact"):
        content_version(ArtifactKind.RDF, b"not valid turtle")


def test_yaml_dates_have_a_portable_identity_distinct_from_strings() -> None:
    plain = content_version(ArtifactKind.YAML, b"released: 2026-01-01\n")
    quoted = content_version(ArtifactKind.YAML, b'released: "2026-01-01"\n')

    assert plain != quoted


def test_yaml_canonical_bytes_keep_dates_as_dates() -> None:
    canonical = canonical_bytes(ArtifactKind.YAML, b"released: 2026-01-01\n")

    assert yaml.safe_load(canonical) == {"released": date(2026, 1, 1)}


def test_yaml_date_does_not_collide_with_a_literal_mapping() -> None:
    plain = content_version(ArtifactKind.YAML, b"released: 2026-01-01\n")
    literal = content_version(ArtifactKind.YAML, b"released:\n  $yaml_type: date\n  value: '2026-01-01'\n")

    assert plain != literal


def test_yaml_identity_ignores_key_order_and_layout() -> None:
    first = content_version(ArtifactKind.YAML, b"b: 1\na: [1, 2]\n")
    second = content_version(ArtifactKind.YAML, b"a:\n  - 1\n  - 2\nb: 1\n")

    assert first == second


@pytest.mark.parametrize("kind", [ArtifactKind.TABLE, ArtifactKind.SSSOM])
def test_table_identity_keeps_cell_whitespace_and_empty_trailing_columns(kind: ArtifactKind) -> None:
    assert content_version(kind, b"id,label\n1,a \n") != content_version(kind, b"id,label\n1,a\n")
    assert content_version(kind, b"id,label,note\n1,a,\n") != content_version(kind, b"id,label,note\n1,a\n")


@pytest.mark.parametrize("kind", [ArtifactKind.TABLE, ArtifactKind.SSSOM])
def test_table_canonical_bytes_preserve_the_original_cells(kind: ArtifactKind) -> None:
    assert canonical_bytes(kind, b"id\tlabel\r\n1\ta \t\r\n\r\n") == b"id\tlabel\n1\ta \t\n"


def test_yaml_identity_ignores_anchors_and_aliases() -> None:
    aliased = content_version(ArtifactKind.YAML, b"a: &x [1]\nb: *x\n")
    expanded = content_version(ArtifactKind.YAML, b"a: [1]\nb: [1]\n")

    assert aliased == expanded
