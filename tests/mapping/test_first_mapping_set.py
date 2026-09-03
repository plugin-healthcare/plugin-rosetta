from pathlib import Path

from plugin_rosetta.application.mapping import read_mapping_set

ROOT = Path(__file__).parents[2]


def test_reads_all_preserved_mappings_in_order() -> None:
    result = read_mapping_set("omop-onz-g", root=ROOT)

    assert result.mapping_set.mappings is not None
    assert len(result.mapping_set.mappings) == 8
    first = result.mapping_set.mappings[0]
    assert first.subject_id == "omop:Person"
    assert first.predicate_id == "skos:exactMatch"
    assert first.object_id == "onz-g:PatientInCare"
    assert first.confidence == 0.9
    assert first.comment is not None
    assert '"Cliënt"@nl' in first.comment
    assert first.author_id == ["orcid:0000-0001-8979-9194"]


def test_mapping_set_metadata_comes_from_configuration() -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=ROOT).mapping_set

    assert mapping_set.mapping_set_id.startswith("https://raw.githubusercontent.com/plugin-healthcare/sssom-rosetta/")
    assert mapping_set.license == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert mapping_set.curie_map is not None
    assert mapping_set.curie_map["omop"] == "https://w3id.org/omop/ontology/"
