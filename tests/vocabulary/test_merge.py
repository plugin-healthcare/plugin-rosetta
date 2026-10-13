from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from plugin_rosetta.errors import VocabularyError
from plugin_rosetta.vocabulary.adapters import get_build_adapter
from plugin_rosetta.vocabulary.merge import merge_graphs, merge_turtle_files
from plugin_rosetta.vocabulary.namespaces import omop_iri, sct_iri

ROOT = Path(__file__).parents[2]
CONFIG = ROOT / "registry/config/vocabulary-sources.yaml"


def test_merge_graphs_collapses_duplicate_triples() -> None:
    triple = (URIRef("https://example.org/s"), URIRef("https://example.org/p"), URIRef("https://example.org/o"))
    first = Graph()
    first.add(triple)
    second = Graph()
    second.add(triple)

    assert len(merge_graphs(first, second)) == 1


def test_merge_turtle_files_uses_maplib_and_writes_atomic_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first.ttl"
    second = tmp_path / "second.ttl"
    first.write_text("<https://example.org/a> <https://example.org/p> <https://example.org/b> .\n")
    second.write_text("<https://example.org/c> <https://example.org/p> <https://example.org/d> .\n")

    def fail_parse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("file merge must not use rdflib")

    monkeypatch.setattr(Graph, "parse", fail_parse)
    output = merge_turtle_files([first, second], tmp_path / "merged.ttl")
    monkeypatch.undo()

    assert len(Graph().parse(output, format="turtle")) == 2


def test_merge_turtle_files_rejects_empty_inputs(tmp_path: Path) -> None:
    with pytest.raises(VocabularyError, match="No vocabulary graph inputs"):
        merge_turtle_files([], tmp_path / "merged.ttl")


def test_merge_connects_omop_extension_and_international_through_shared_snomed_iris(tmp_path: Path) -> None:
    output_dir = tmp_path / "graphs"
    omop, _ = get_build_adapter("omop").build(
        ROOT / "tests/fixtures/vocabulary/athena",
        output_dir,
        config_path=CONFIG,
        as_of=None,
    )
    extension, _ = get_build_adapter("loinc-snomed").build(
        ROOT / "tests/fixtures/vocabulary/rf2",
        output_dir,
        config_path=CONFIG,
        as_of=None,
    )
    international, _ = get_build_adapter("snomed-international").build(
        ROOT / "tests/fixtures/vocabulary/rf2",
        output_dir,
        config_path=CONFIG,
        as_of=None,
    )

    merged_path = merge_turtle_files([omop, extension, international], tmp_path / "merged.ttl")
    merged = Graph().parse(merged_path, format="turtle")

    shared = sct_iri("123456789012345678")
    parent = sct_iri("73211009")
    assert (omop_iri("SYNTHETIC-OMOP-2"), SKOS.exactMatch, shared) in merged
    assert (shared, RDFS.subClassOf, parent) in merged
    assert (parent, RDF.type, SKOS.Concept) in merged
