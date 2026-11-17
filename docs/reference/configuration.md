# Configuration

Every YAML file in a registry is read into one of the Pydantic models on this page.
The attributes of each model are the keys you can write in the YAML file, and unknown keys are rejected.
Paths in the configuration are relative to the workspace root, except table `contract` paths, which are relative to the registry directory.

See [Registry](../background/registry.md) for how these files fit together.

## Workspace: `rosetta.yaml`

::: plugin_rosetta.workspace
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3

## Mapping sets: `config/mapping-sets.yaml`

```yaml
mapping_sets:
  omop-onz-g:
    mapping_set_id: https://example.org/mappings/omop-onz-g.sssom.tsv
    license: https://creativecommons.org/publicdomain/zero/1.0/
    mapping_file: registry/mappings/omop-onz-g.csv
    metadata_file: registry/mappings/omop-onz-g.metadata.json
    curie_map:
      omop: https://w3id.org/omop/ontology/
      onz-g: http://purl.org/ozo/onz-g#
      skos: http://www.w3.org/2004/02/skos/core#
    ontologies:
      subject: omop-cdm
      object: onz-g
```

::: plugin_rosetta.mapping.config
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
      members:
        - MappingSetsConfig
        - MappingSetConfig
        - MappingSetOntologies
        - load_mapping_sets

## Ontology sources: `config/ontology-sources.yaml`

```yaml
ontology_sources:
  omop-cdm:
    version: "5.4"
    iri: https://w3id.org/omop/ontology
    download_url: https://example.org/omop_cdm_v5.ttl
    checksum: 3f2a...  # 64 lowercase hexadecimal characters
```

::: plugin_rosetta.ontology.config
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
      members:
        - OntologySourcesConfig
        - OntologySourceEntry
        - OntologySource
        - load_ontology_sources

## Vocabulary sources: `config/vocabulary-sources.yaml`

```yaml
vocabulary_sources:
  snomed-international:
    version: "20260101"
    kind: rf2
    language_refset_id: "900000000000509007"
    description: SNOMED CT International Edition distributed as an RF2 package.
    download_page: https://www.nlm.nih.gov/healthit/snomedct/international.html
    tables:
      - role: concept
        prefix: sct2_Concept_Snapshot
        suffix: .txt
        contains: /Snapshot/
        separator: "\t"
        contract: schemas/vocabularies/rf2-concept.yaml
```

::: plugin_rosetta.vocabulary.config
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
      members:
        - VocabularySourcesConfig
        - VocabularySourceEntry
        - VocabularySource
        - ReleaseTable
        - load_vocabulary_sources

## Table contracts: `schemas/vocabularies/*.yaml`

A table contract lists the columns that a release table must contain.
Each column has a `dtype` (`String`, `Int64`, `Float64`, or `Boolean`) and an optional `nullable` flag, which defaults to true.
Missing columns, incompatible types, and nulls in non-nullable columns are errors.
Extra columns are kept and reported as informational findings.

```yaml
columns:
  concept_id:
    dtype: String
    nullable: false
  standard_concept:
    dtype: String
```
