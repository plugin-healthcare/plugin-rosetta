"""Merge vocabulary graphs in memory or through Maplib's file path."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from maplib import MaplibException, Model
from rdflib import Graph
from rdflib.namespace import OWL, SKOS

from plugin_rosetta.errors import RosettaIOError, VocabularyError
from plugin_rosetta.utils.io.atomic import atomic_write_bytes
from plugin_rosetta.vocabulary.namespaces import PREFIX_MAP

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib.term import Node


class _MaplibModel(Protocol):
    def writes(self, format_: str) -> str:
        """Serialize the model to an RDF string."""
        ...


def _iter_triples(graph: Graph | _MaplibModel) -> Iterator[tuple[Node, Node, Node]]:
    if isinstance(graph, Graph):
        yield from graph
        return
    reparsed = Graph().parse(data=graph.writes("ntriples"), format="ntriples")
    yield from reparsed


def merge_graphs(*graphs: Graph | _MaplibModel) -> Graph:
    """Return the set union of RDFLib and Maplib graph objects."""
    merged = Graph()
    for prefix, namespace in PREFIX_MAP.items():
        merged.bind(prefix, namespace)
    merged.bind("skos", SKOS)
    merged.bind("owl", OWL)
    for graph in graphs:
        for triple in _iter_triples(graph):
            merged.add(triple)
    return merged


def merge_turtle_files(inputs: list[Path], output_path: Path) -> Path:
    """Merge Turtle files through Maplib and atomically replace the output."""
    if not inputs:
        raise VocabularyError("No vocabulary graph inputs were provided for merge")
    missing = [path for path in inputs if not path.is_file()]
    if missing:
        raise VocabularyError(f"Missing vocabulary graph inputs: {', '.join(str(path) for path in missing)}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model = Model()
        for path in inputs:
            model.read(str(path), format="turtle", parallel=True)
        with tempfile.TemporaryDirectory(dir=output_path.parent, prefix=f".{output_path.name}.") as temporary_dir:
            temporary_path = Path(temporary_dir) / output_path.name
            model.write(str(temporary_path), format="turtle")
            content = temporary_path.read_bytes()
    except (MaplibException, OSError) as error:
        raise RosettaIOError(f"Cannot merge vocabulary graphs into {output_path}: {error}") from error
    atomic_write_bytes(output_path, content)
    return output_path
