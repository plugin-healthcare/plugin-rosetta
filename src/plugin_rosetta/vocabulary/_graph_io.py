"""Atomic serialization for Maplib RDF graphs."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from maplib import MaplibException, Model
from rdflib import Graph

from plugin_rosetta.errors import RosettaIOError
from plugin_rosetta.utils.io.atomic import atomic_write_bytes

if TYPE_CHECKING:
    from collections.abc import Mapping


def _render_deterministic_turtle(content: bytes, prefixes: Mapping[str, str]) -> str:
    graph = Graph().parse(data=content, format="turtle")
    declarations = [f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in sorted(prefixes.items())]
    triples = sorted(f"{subject.n3()} {predicate.n3()} {object_.n3()} ." for subject, predicate, object_ in graph)
    return "\n".join([*declarations, "", *triples, ""])


def write_turtle(
    model: Model,
    destination: Path,
    *,
    prefixes: Mapping[str, str],
) -> Path:
    """Write a Maplib model as Turtle using atomic final replacement."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destination.parent, prefix=f".{destination.name}.") as temporary_dir:
            temporary_path = Path(temporary_dir) / destination.name
            model.write(str(temporary_path), format="turtle")
            content = _render_deterministic_turtle(temporary_path.read_bytes(), prefixes)
    except (MaplibException, OSError) as error:
        raise RosettaIOError(f"Cannot serialize Turtle to {destination}: {error}") from error
    atomic_write_bytes(destination, content.encode())
    return destination


def write_rdflib_turtle(
    graph: Graph,
    destination: Path,
    *,
    prefixes: Mapping[str, str],
) -> Path:
    """Write an RDFLib graph deterministically using atomic replacement."""
    declarations = [f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in sorted(prefixes.items())]
    triples = sorted(f"{subject.n3()} {predicate.n3()} {object_.n3()} ." for subject, predicate, object_ in graph)
    atomic_write_bytes(destination, "\n".join([*declarations, "", *triples, ""]).encode())
    return destination
