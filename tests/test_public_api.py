from importlib.resources import files

from plugin_rosetta import RosettaError, ValidationReport
from plugin_rosetta.mapping import build_mapping_artifacts, read_mapping_set
from plugin_rosetta.ontology import fetch_ontology_source
from plugin_rosetta.vocabulary import build_omop_graph, ingest_release
from plugin_rosetta.workspace import initialize_workspace


def test_feature_packages_expose_supported_library_operations() -> None:
    assert callable(build_mapping_artifacts)
    assert callable(read_mapping_set)
    assert callable(fetch_ontology_source)
    assert callable(build_omop_graph)
    assert callable(ingest_release)
    assert callable(initialize_workspace)
    assert issubclass(RosettaError, Exception)
    assert ValidationReport().is_valid


def test_installed_package_declares_inline_types() -> None:
    assert files("plugin_rosetta").joinpath("py.typed").is_file()
