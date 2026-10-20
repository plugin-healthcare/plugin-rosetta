# Vocabulary

Ingest licence-gated terminology releases and build them into RDF graphs.
Import these names from `plugin_rosetta.vocabulary`.

::: plugin_rosetta.vocabulary
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - ingest_release
        - build_omop_graph
        - build_cached_omop_graph
        - build_dhd_graph
        - build_cached_dhd_graph
        - build_rf2_graph
        - build_cached_rf2_graph
        - merge_built_vocabulary_graphs
        - DEFAULT_VOCABULARY_CONFIG
        - DEFAULT_VOCABULARY_OUTPUT_DIR

## Adapter contract

A vocabulary source format is supported through a build adapter.
See [Onboarding a Standard and Mapping](../guides/onboarding.md) for when you need a new one.

::: plugin_rosetta.vocabulary.adapters.BuildAdapter
    options:
      heading_level: 3

The configuration models `VocabularySourcesConfig`, `VocabularySourceEntry`, `VocabularySource`, `ReleaseTable`, and `load_vocabulary_sources` are documented on the [Configuration](configuration.md) page.
