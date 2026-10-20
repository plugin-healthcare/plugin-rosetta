# Ontology

Fetch and cache pinned ontology sources that mapping sets are checked against.
Import these names from `plugin_rosetta.ontology`.

::: plugin_rosetta.ontology
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - fetch_ontology_source
        - DEFAULT_ONTOLOGY_CONFIG

The configuration models `OntologySourcesConfig`, `OntologySourceEntry`, `OntologySource`, and `load_ontology_sources` are documented on the [Configuration](configuration.md) page.
