import pytest

from plugin_rosetta.artifacts.identity import ArtifactKind, content_version
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
