from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest

from plugin_rosetta.errors import ValidationError, VocabularyError
from plugin_rosetta.vocabulary import load_vocabulary_sources
from plugin_rosetta.vocabulary.adapters.thesaurus import (
    DhdCrossLinks,
    build_from_release,
    build_graph,
    load_concepts,
    load_dbc,
    load_icd10,
    load_labels,
    load_snomed_terms,
)
from plugin_rosetta.vocabulary.frames import load_table_contract
from plugin_rosetta.vocabulary.namespaces import ICD10, dbc_iri, dhd_concept_iri, sct_iri

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary import ReleaseTable

ROOT = Path(__file__).parents[3]
FIXTURE_DIR = ROOT / "tests/fixtures/vocabulary/dhd"
CONFIG_PATH = ROOT / "registry/config/vocabulary-sources.yaml"
REGISTRY_ROOT = ROOT / "registry"
AS_OF = "20260910"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SKOS = "http://www.w3.org/2004/02/skos/core#"


def _table(thesaurus: str, table_type: str) -> ReleaseTable:
    source = load_vocabulary_sources(CONFIG_PATH).get("dhd-thesauri")
    return next(table for table in source.tables if table.role == f"{thesaurus}-{table_type}")


def _contract(table: ReleaseTable):
    return load_table_contract(REGISTRY_ROOT / table.contract)


def _objects(model, subject: str, predicate: str) -> list[str]:
    query = f"SELECT ?object WHERE {{ <{subject}> <{predicate}> ?object }}"
    return model.query(query)["object"].to_list()


def _iris(model, subject: str, predicate: str) -> list[str]:
    return [value.removeprefix("<").removesuffix(">") for value in _objects(model, subject, predicate)]


def test_loaders_read_quoted_text_and_filter_each_validity_window() -> None:
    release_dir = FIXTURE_DIR / "thesauri/DT/202609_uitleverformaat4.3"
    concept_table = _table("dt", "concept")
    term_table = _table("dt", "term")

    concepts = load_concepts(
        release_dir / "SYN_ThesaurusConcept.csv",
        concept_table,
        _contract(concept_table),
        AS_OF,
    )
    labels = load_labels(
        release_dir / "SYN_ThesaurusTerm.csv",
        term_table,
        _contract(term_table),
        AS_OF,
    )

    assert concepts.rows() == [("0000000001",), ("0000000002",)]
    assert labels.sort("ConceptID").to_dicts() == [
        {"ConceptID": "0000000001", "Omschrijving": 'Cyste, "nader omschreven"', "Language": "nl"},
        {"ConceptID": "0000000002", "Omschrijving": "Fracture (disorder)", "Language": "en"},
    ]


def test_load_snomed_terms_deduplicates_concurrent_fsn_languages() -> None:
    release_dir = FIXTURE_DIR / "thesauri/DT/202609_uitleverformaat4.3"
    table = _table("dt", "term")

    terms = load_snomed_terms(
        release_dir / "SYN_ThesaurusTerm.csv",
        table,
        _contract(table),
        AS_OF,
    )

    assert terms.sort("ConceptID").rows() == [
        ("0000000001", "39462005"),
        ("0000000002", "125605004"),
    ]


def test_derivation_loaders_keep_all_active_codes_and_scope_dbc_identity() -> None:
    release_dir = FIXTURE_DIR / "thesauri/DT/202609_uitleverformaat4.3"
    icd10_table = _table("dt", "icd10")
    dbc_table = _table("dt", "dbc")

    icd10 = load_icd10(
        release_dir / "SYN_AfleidingICD10.csv",
        icd10_table,
        _contract(icd10_table),
        AS_OF,
    )
    dbc = load_dbc(
        release_dir / "SYN_AfleidingDBC.csv",
        dbc_table,
        _contract(dbc_table),
        AS_OF,
    )

    assert sorted(icd10.rows()) == [
        ("0000000001", "G52.3"),
        ("0000000001", "G52.4"),
    ]
    assert sorted(dbc.rows()) == [
        ("0000000001", "0389-411"),
        ("0000000001", "3308-411"),
    ]


@pytest.mark.parametrize("invalid_date", ["2026-09-10", "2026091", "abcdefgh"])
def test_loaders_reject_malformed_as_of_dates(invalid_date: str) -> None:
    release_dir = FIXTURE_DIR / "thesauri/DT/202609_uitleverformaat4.3"
    table = _table("dt", "concept")

    with pytest.raises(ValidationError, match="YYYYMMDD"):
        load_concepts(
            release_dir / "SYN_ThesaurusConcept.csv",
            table,
            _contract(table),
            invalid_date,
        )


def test_loaders_reject_impossible_calendar_dates_in_release_rows(tmp_path: Path) -> None:
    path = tmp_path / "SYN_ThesaurusConcept.csv"
    path.write_text('ConceptID,Begindatum,Einddatum\n"1","20260230",""\n')
    table = _table("dt", "concept")

    with pytest.raises(ValidationError, match=r"Begindatum.*20260230.*YYYYMMDD"):
        load_concepts(path, table, _contract(table), AS_OF)


def test_load_labels_omits_label_without_language(tmp_path: Path) -> None:
    path = tmp_path / "SYN_ThesaurusTerm.csv"
    path.write_text(
        "ConceptID,Omschrijving,TaalCode,TypeTerm,SnomedID,Begindatum,Einddatum\n"
        '"1","Label without language","","FSN","39462005","20260101",""\n'
    )
    table = _table("dt", "term")

    labels = load_labels(path, table, _contract(table), AS_OF)

    assert labels.is_empty()


def test_build_graph_preserves_optional_values_and_dt_crosslinks() -> None:
    concepts = pl.DataFrame({"ConceptID": ["1", "2"]})
    snomed = pl.DataFrame({"ConceptID": ["1"], "SnomedID": ["39462005"]})
    labels = pl.DataFrame({"ConceptID": ["1"], "Omschrijving": ["cyste"], "Language": ["nl"]})
    cross_links = DhdCrossLinks(
        icd10=pl.DataFrame({"ConceptID": ["1"], "ICD10": ["G52.3"]}),
        dbc=pl.DataFrame({"ConceptID": ["1"], "DBC_ID": ["0389-130"]}),
    )

    model = build_graph("dt", concepts, snomed, labels, cross_links)

    concept = str(dhd_concept_iri("dt", "1"))
    empty_concept = str(dhd_concept_iri("dt", "2"))
    assert _iris(model, concept, RDF_TYPE) == [f"{SKOS}Concept"]
    assert _objects(model, concept, f"{SKOS}prefLabel") == ['"cyste"@nl']
    assert _iris(model, concept, f"{SKOS}exactMatch") == [str(sct_iri("39462005"))]
    assert sorted(_iris(model, concept, f"{SKOS}closeMatch")) == sorted([str(ICD10["G52.3"]), str(dbc_iri("0389-130"))])
    assert _iris(model, empty_concept, RDF_TYPE) == [f"{SKOS}Concept"]
    assert _objects(model, empty_concept, f"{SKOS}prefLabel") == []
    assert _objects(model, empty_concept, f"{SKOS}exactMatch") == []


def test_build_from_release_separates_dt_and_vt_namespaces() -> None:
    source = load_vocabulary_sources(CONFIG_PATH).get("dhd-thesauri")

    dt_model = build_from_release(FIXTURE_DIR, "dt", source, REGISTRY_ROOT, as_of=AS_OF)
    vt_model = build_from_release(FIXTURE_DIR, "vt", source, REGISTRY_ROOT, as_of=AS_OF)

    dt_concept = str(dhd_concept_iri("dt", "0000000001"))
    vt_concept = str(dhd_concept_iri("vt", "0000000001"))
    assert dt_concept != vt_concept
    assert _iris(dt_model, dt_concept, f"{SKOS}closeMatch")
    assert _iris(vt_model, vt_concept, f"{SKOS}exactMatch") == [str(sct_iri("39462005"))]
    assert _objects(vt_model, vt_concept, f"{SKOS}closeMatch") == []


def test_build_from_release_names_wrong_or_ambiguous_format_directories(tmp_path: Path) -> None:
    source = load_vocabulary_sources(CONFIG_PATH).get("dhd-thesauri")
    wrong = tmp_path / "thesauri/DT/release_uitleverformaat5.0"
    wrong.mkdir(parents=True)

    with pytest.raises(VocabularyError, match=r"uitleverformaat4\.3.*uitleverformaat5\.0"):
        build_from_release(tmp_path, "dt", source, REGISTRY_ROOT, as_of=AS_OF)

    first = tmp_path / "thesauri/DT/first_uitleverformaat4.3"
    second = tmp_path / "thesauri/DT/second_uitleverformaat4.3"
    first.mkdir()
    second.mkdir()
    with pytest.raises(VocabularyError, match=r"first_uitleverformaat4\.3.*second_uitleverformaat4\.3"):
        build_from_release(tmp_path, "dt", source, REGISTRY_ROOT, as_of=AS_OF)
