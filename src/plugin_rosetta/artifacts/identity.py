"""Canonical content identities for local artifacts."""

import hashlib
import json
from enum import StrEnum

import yaml
from rdflib import Graph
from rdflib.compare import to_canonical_graph
from rdflib.exceptions import ParserError

from plugin_rosetta.errors import ArtifactError


class ArtifactKind(StrEnum):
    """Artifact formats with distinct canonicalisation rules."""

    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    RDF = "rdf"
    SSSOM = "sssom"
    TABLE = "table"
    TEXT = "text"
    YAML = "yaml"


def _canonical_text(content: bytes) -> bytes:
    try:
        text = content.decode()
    except UnicodeDecodeError as error:
        raise ArtifactError("Text artifacts must be UTF-8") from error
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return ("\n".join(lines) + "\n").encode()


class _ExpandedDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: object) -> bool:
        return True


def _canonical_table(content: bytes) -> bytes:
    try:
        text = content.decode()
    except UnicodeDecodeError as error:
        raise ArtifactError("Table artifacts must be UTF-8") from error
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return ("\n".join(lines) + "\n").encode()


def _canonical_structured(content: bytes, kind: ArtifactKind) -> bytes:
    try:
        if kind is ArtifactKind.JSON:
            value = json.loads(content)
            return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        return yaml.dump(yaml.safe_load(content), Dumper=_ExpandedDumper, sort_keys=True, allow_unicode=False).encode()
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ArtifactError(f"Cannot parse {kind.value} artifact: {error}") from error


def _canonical_rdf(content: bytes) -> bytes:
    try:
        graph = Graph().parse(data=content.decode(), format="turtle")
    except (UnicodeDecodeError, ParserError, SyntaxError, ValueError) as error:
        raise ArtifactError(f"Cannot parse RDF artifact: {error}") from error
    serialized = to_canonical_graph(graph).serialize(format="nt")
    return "".join(sorted(serialized.splitlines(keepends=True))).encode()


def canonical_bytes(kind: ArtifactKind, content: bytes) -> bytes:
    """Return the documented canonical representation for an artifact."""
    if kind is ArtifactKind.RDF:
        return _canonical_rdf(content)
    if kind in {ArtifactKind.JSON, ArtifactKind.YAML}:
        return _canonical_structured(content, kind)
    if kind in {ArtifactKind.TABLE, ArtifactKind.SSSOM}:
        return _canonical_table(content)
    return _canonical_text(content)


def content_version(kind: ArtifactKind, content: bytes) -> str:
    """Return a kind-scoped SHA-256 version for canonical artifact bytes."""
    digest = hashlib.sha256()
    digest.update(kind.value.encode())
    digest.update(b"\0")
    digest.update(canonical_bytes(kind, content))
    return digest.hexdigest()
