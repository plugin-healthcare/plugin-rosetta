from pathlib import Path

from rdflib import Literal
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from plugin_rosetta.vocabulary import load_vocabulary_sources
from plugin_rosetta.vocabulary.adapters.rf2 import (
    active_rows,
    build_graph,
    isa_edges,
    preferred_terms,
    read_rf2,
    synonyms,
)
from plugin_rosetta.vocabulary.frames import load_table_contract
from plugin_rosetta.vocabulary.ingest import find_file
from plugin_rosetta.vocabulary.namespaces import sct_iri

ROOT = Path(__file__).parents[3]
FIXTURE = ROOT / "tests/fixtures/vocabulary/rf2"
CONFIG = ROOT / "registry/config/vocabulary-sources.yaml"


def _frame(role: str):
    table = next(table for table in load_vocabulary_sources(CONFIG).get("loinc-snomed").tables if table.role == role)
    path = find_file(
        FIXTURE,
        name=table.name,
        prefix=table.prefix,
        suffix=table.suffix,
        contains=table.contains,
    )
    return read_rf2(path, table, load_table_contract(ROOT / "registry" / table.contract))


def test_rf2_reader_preserves_quotes_and_long_identifiers_as_text() -> None:
    concepts = _frame("concept")
    descriptions = _frame("description")

    assert "123456789012345678" in concepts["id"]
    assert 'Glucose "measurement" finding' in descriptions["term"]
    assert "Glucose 'test'" in descriptions["term"]


def test_rf2_transforms_active_hierarchy_and_labels() -> None:
    concepts = _frame("concept")
    descriptions = _frame("description")
    language = _frame("language")
    relationships = _frame("relationship")

    assert active_rows(concepts).height == 2
    assert isa_edges(relationships).rows() == [("123456789012345678", "73211009")]
    language_refset_id = "900000000000509007"
    assert preferred_terms(descriptions, language, language_refset_id).rows() == [
        ("123456789012345678", "Glucose 'test'", "en"),
        ("73211009", "Diabetes", "en"),
    ]
    assert synonyms(descriptions, language, language_refset_id).rows() == [
        ("123456789012345678", "Blood glucose assay", "en")
    ]

    graph = build_graph(concepts, descriptions, language, relationships, language_refset_id)
    concept = sct_iri("123456789012345678")
    parent = sct_iri("73211009")
    assert (concept, RDF.type, SKOS.Concept) in graph
    assert (concept, RDF.type, OWL.Class) in graph
    assert (concept, SKOS.prefLabel, Literal("Glucose 'test'", lang="en")) in graph
    assert (concept, SKOS.altLabel, Literal("Blood glucose assay", lang="en")) in graph
    assert (concept, SKOS.altLabel, Literal("Glucose 'test'", lang="en")) not in graph
    assert (concept, RDFS.subClassOf, parent) in graph
    assert (concept, SKOS.broadMatch, parent) in graph
