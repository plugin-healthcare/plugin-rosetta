from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.vocabulary import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract
from plugin_rosetta.vocabulary.namespaces import omop_iri, sct_iri, source_concept_iri
from plugin_rosetta.vocabulary.omop import (
    build_graph,
    load_relationship_types,
    load_relationships,
    load_target_concepts,
)

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary import ReleaseTable

ROOT = Path(__file__).parents[2]
FIXTURE_DIR = ROOT / "tests/fixtures/vocabulary/athena"
CONFIG_PATH = ROOT / "registry/config/vocabulary-sources.yaml"
REGISTRY_ROOT = ROOT / "registry"


def _table(name: str) -> ReleaseTable:
    source = load_vocabulary_sources(CONFIG_PATH).get("omop")
    return next(table for table in source.tables if table.name == name)


def _objects(model, subject: str, predicate: str) -> list[str]:
    query = f"SELECT ?object WHERE {{ <{subject}> <{predicate}> ?object }}"
    return model.query(query)["object"].to_list()


def _iris(model, subject: str, predicate: str) -> list[str]:
    return [value.removeprefix("<").removesuffix(">") for value in _objects(model, subject, predicate)]


def test_load_target_concepts_uses_declared_athena_reader_and_filters_early() -> None:
    table = _table("CONCEPT.csv")

    concepts = load_target_concepts(
        FIXTURE_DIR / table.name,
        table,
        load_table_contract(REGISTRY_ROOT / table.contract),
    )

    assert concepts.columns == ["concept_id", "concept_name", "vocabulary_id", "concept_code"]
    assert "SYNTHETIC-OUTSIDE" not in concepts["concept_id"]
    assert 'Aspirin 81 MG "low dose"' in concepts["concept_name"]
    assert "123456789012345678" in concepts["concept_code"]


def test_load_target_concepts_validates_before_transforming(tmp_path: Path) -> None:
    table = _table("CONCEPT.csv")
    invalid_path = tmp_path / table.name
    invalid_path.write_text("concept_id\tconcept_name\n1001\tIncomplete\n")

    with pytest.raises(ValidationError, match="Missing expected columns"):
        load_target_concepts(
            invalid_path,
            table,
            load_table_contract(REGISTRY_ROOT / table.contract),
        )


def test_load_target_concepts_explains_unsupported_embedded_newline(tmp_path: Path) -> None:
    table = _table("CONCEPT.csv")
    concept_path = tmp_path / table.name
    concept_path.write_text(
        "concept_id\tconcept_name\tdomain_id\tvocabulary_id\tconcept_class_id\tstandard_concept\t"
        "concept_code\tvalid_start_date\tvalid_end_date\tinvalid_reason\n"
        "1001\tBroken\nname\tCondition\tSNOMED\tClinical Finding\tS\t44054006\t20260101\t20991231\t\n"
    )

    with pytest.raises(ValidationError, match="embedded newlines cannot be represented"):
        load_target_concepts(
            concept_path,
            table,
            load_table_contract(REGISTRY_ROOT / table.contract),
        )


def test_load_relationships_keeps_only_current_in_scope_edges() -> None:
    concept_table = _table("CONCEPT.csv")
    concepts = load_target_concepts(
        FIXTURE_DIR / concept_table.name,
        concept_table,
        load_table_contract(REGISTRY_ROOT / concept_table.contract),
    )
    relationship_table = _table("CONCEPT_RELATIONSHIP.csv")

    relationships = load_relationships(
        FIXTURE_DIR / relationship_table.name,
        relationship_table,
        load_table_contract(REGISTRY_ROOT / relationship_table.contract),
        concepts["concept_id"],
    )

    assert relationships.rows() == [
        ("SYNTHETIC-OMOP-1", "SYNTHETIC-OMOP-2", "Maps to"),
        ("SYNTHETIC-OMOP-5", "SYNTHETIC-OMOP-6", "RxNorm has ing"),
    ]


def test_source_concept_iri_handles_supported_and_native_less_vocabularies() -> None:
    assert source_concept_iri("SNOMED", "123456789012345678") == sct_iri("123456789012345678")
    assert source_concept_iri("RxNorm Extension", "") is None
    assert str(source_concept_iri("LOINC", "H&P.SURG PROC")) == "https://loinc.org/H%26P.SURG%20PROC"


@pytest.mark.parametrize(
    ("vocabulary_id", "code", "expected"),
    [
        ("SNOMED", "44054006", "http://snomed.info/id/44054006"),
        ("LOINC", "2345-7", "https://loinc.org/2345-7"),
        ("RxNorm", "202433", "http://purl.bioontology.org/ontology/RXNORM/202433"),
        ("ICD10", "E11.9", "http://hl7.org/fhir/sid/icd-10/E11.9"),
        ("ICD10CM", "E11.9", "http://hl7.org/fhir/sid/icd-10-cm/E11.9"),
    ],
)
def test_source_concept_iri_mints_every_supported_native_namespace(
    vocabulary_id: str,
    code: str,
    expected: str,
) -> None:
    assert str(source_concept_iri(vocabulary_id, code)) == expected


def test_build_graph_emits_concepts_crosslinks_relationships_and_used_labels() -> None:
    concept_table = _table("CONCEPT.csv")
    concepts = load_target_concepts(
        FIXTURE_DIR / concept_table.name,
        concept_table,
        load_table_contract(REGISTRY_ROOT / concept_table.contract),
    )
    relationship_table = _table("CONCEPT_RELATIONSHIP.csv")
    relationships = load_relationships(
        FIXTURE_DIR / relationship_table.name,
        relationship_table,
        load_table_contract(REGISTRY_ROOT / relationship_table.contract),
        concepts["concept_id"],
    )
    type_table = _table("RELATIONSHIP.csv")
    relationship_types = load_relationship_types(
        FIXTURE_DIR / type_table.name,
        type_table,
        load_table_contract(REGISTRY_ROOT / type_table.contract),
    )

    model = build_graph(concepts, relationships, relationship_types)

    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    skos = "http://www.w3.org/2004/02/skos/core#"
    loinc_node = str(omop_iri("SYNTHETIC-OMOP-1"))
    assert _iris(model, loinc_node, rdf_type) == [f"{skos}Concept"]
    assert _objects(model, loinc_node, f"{skos}prefLabel") == ['"Glucose [Mass/volume]"@en']
    assert _objects(model, loinc_node, f"{skos}notation") == ["H&P.SURG PROC"]
    assert _iris(model, loinc_node, f"{skos}exactMatch") == ["https://loinc.org/H%26P.SURG%20PROC"]

    extension_node = str(omop_iri("SYNTHETIC-OMOP-3"))
    assert _iris(model, extension_node, rdf_type) == [f"{skos}Concept"]
    assert _objects(model, extension_node, f"{skos}exactMatch") == []

    maps_to = str(omop_iri("44818977"))
    assert _iris(model, loinc_node, maps_to) == [str(omop_iri("SYNTHETIC-OMOP-2"))]
    assert _objects(model, maps_to, f"{skos}prefLabel") == ['"Maps to (OMOP)"@en']
    assert _objects(model, str(omop_iri("44818723")), f"{skos}prefLabel") == []


def test_optional_concept_values_emit_no_optional_triples() -> None:
    concepts = pl.DataFrame(
        {
            "concept_id": ["1"],
            "concept_name": [None],
            "vocabulary_id": ["LOINC"],
            "concept_code": [None],
        },
        schema={
            "concept_id": pl.String,
            "concept_name": pl.String,
            "vocabulary_id": pl.String,
            "concept_code": pl.String,
        },
    )

    model = build_graph(
        concepts,
        pl.DataFrame(schema={"concept_id_1": pl.String, "concept_id_2": pl.String, "relationship_id": pl.String}),
        pl.DataFrame(
            schema={
                "relationship_id": pl.String,
                "relationship_concept_id": pl.String,
                "relationship_name": pl.String,
            }
        ),
    )

    node = str(omop_iri("1"))
    skos = "http://www.w3.org/2004/02/skos/core#"
    assert _objects(model, node, f"{skos}prefLabel") == []
    assert _objects(model, node, f"{skos}notation") == []
    assert _objects(model, node, f"{skos}exactMatch") == []


def test_build_graph_rejects_relationship_without_predicate_concept() -> None:
    relationships = pl.DataFrame(
        {
            "concept_id_1": ["1"],
            "concept_id_2": ["2"],
            "relationship_id": ["Unknown relationship"],
        }
    )
    relationship_types = pl.DataFrame(
        schema={
            "relationship_id": pl.String,
            "relationship_concept_id": pl.String,
            "relationship_name": pl.String,
        }
    )

    with pytest.raises(ValidationError, match="Unknown relationship"):
        build_graph(
            pl.DataFrame(
                {
                    "concept_id": ["1", "2"],
                    "concept_name": ["One", "Two"],
                    "vocabulary_id": ["LOINC", "LOINC"],
                    "concept_code": ["1", "2"],
                }
            ),
            relationships,
            relationship_types,
        )
