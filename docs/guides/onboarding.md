# Onboarding a Standard and Mapping

This guide adds a standard to the registry and a mapping set that uses it.
Paths are relative to the workspace root, and the [configuration reference](../reference/configuration.md) lists every key.
Examples that refer to existing entries, such as `onz-g`, need a checkout of this repository or copies of those files.

Pick the section that fits the standard:

- A data model published as one Turtle file at a stable URL is an **ontology source**, see [Add an ontology source](#add-an-ontology-source).
- A licensed terminology release in `athena`, `dhd-csv`, or `rf2` format is a **vocabulary source**, see [Add a vocabulary source](#add-a-vocabulary-source).
- A release in another format needs a new adapter, see [Add a new vocabulary format](#add-a-new-vocabulary-format).

## Add an ontology source

1. Copy the download URL of the Turtle file from the publisher's page.
   Prefer a URL that never changes, such as a raw GitHub URL pinned to a commit.
2. Add an entry to `registry/config/ontology-sources.yaml`.
   Use lowercase letters, digits, and hyphens in the key.

    ```yaml
    ontology_sources:
      my-model:
        version: "1.0.0"
        iri: https://example.org/my-model
        download_url: https://raw.githubusercontent.com/example/my-model/<commit>/my-model.ttl
    ```

3. Download and cache it.

    ```shell
    uv run rosetta ontology fetch my-model
    ```

4. Confirm the file is the expected version, then add the printed SHA-256 as `checksum` to the entry.

## Add a vocabulary source

1. Add an entry to `registry/config/vocabulary-sources.yaml`.
   Copy an existing entry of the same `kind` and change the name, version, description, and download page.
   The values below are illustrative.

    ```yaml
    vocabulary_sources:
      snomed-nl:
        version: "20260930"
        kind: rf2
        language_refset_id: "31000146106"
        description: SNOMED CT Netherlands Edition distributed as an RF2 package.
        download_page: https://mlds.ihtsdotools.org/
        tables:
          - role: concept
            prefix: sct2_Concept_Snapshot
            suffix: .txt
            contains: /Snapshot/
            separator: "\t"
            contract: schemas/vocabularies/rf2-concept.yaml
          # description, language, and relationship roles follow the same pattern
    ```

2. Download the release ZIP by hand and ingest it.

    ```shell
    uv run rosetta vocabulary ingest snomed-nl ~/Downloads/release.zip
    ```

    Add the printed SHA-256 as `checksum` once you have confirmed the release.

3. Register a build adapter in `_ADAPTERS` in `src/plugin_rosetta/vocabulary/adapters/__init__.py`, for example `"snomed-nl": Rf2BuildAdapter("snomed-nl", "snomed-nl.ttl")`.
4. Add a matching `build-snomed-nl` command in `src/plugin_rosetta/cli.py` next to the existing RF2 commands, and a test with synthetic data.
5. Build the graph.

    ```shell
    uv run rosetta vocabulary build-snomed-nl
    ```

Mapping references cannot be checked against vocabulary graphs yet.

## Add a new vocabulary format

1. Write a table contract in `registry/schemas/vocabularies/` for every table you need.
2. Add the format name to the `kind` field of `VocabularySourceEntry` in `src/plugin_rosetta/vocabulary/config.py`.
3. Add the source to `registry/config/vocabulary-sources.yaml`, with one `tables` entry per role.
4. Write an adapter in `src/plugin_rosetta/vocabulary/adapters/` that implements the [`BuildAdapter`](../reference/vocabulary.md#adapter-contract) contract.
5. Add namespaces for any new code system to `src/plugin_rosetta/vocabulary/namespaces.py`.
6. Register the adapter in `_ADAPTERS`, add a CLI command, and add tests with a small synthetic fixture under `tests/fixtures/vocabulary/`.
7. Run `uv run tara check` until it passes.

## Add a mapping set

1. Create `registry/mappings/my-set.csv` with one row per mapping.

    ```csv
    subject_id,predicate_id,object_id,mapping_justification,confidence,author_id,author_label,reviewer_id,subject_label,object_label,comment
    my-model:Patient,skos:exactMatch,onz-g:PatientInCare,semapv:ManualMappingCuration,0.9,orcid:0000-0000-0000-0000,Jane Doe,,Patient,Cliënt,Why this predicate was chosen.
    ```

    `subject_id`, `predicate_id`, `object_id`, and `mapping_justification` are required.
    Write the ids as CURIEs with a prefix from the `curie_map`.

2. Copy `registry/mappings/omop-onz-g.metadata.json` to `registry/mappings/my-set.metadata.json`.
   Change `url` to `my-set.csv` and update `dc:title` and `dc:description`.
   Keep the `primaryKey`, because Rosetta uses it to reject duplicate mappings.
3. Add the set to `registry/config/mapping-sets.yaml`.

    ```yaml
    mapping_sets:
      my-set:
        mapping_set_id: https://example.org/mappings/my-set.sssom.tsv
        license: https://creativecommons.org/publicdomain/zero/1.0/
        mapping_file: registry/mappings/my-set.csv
        metadata_file: registry/mappings/my-set.metadata.json
        curie_map:
          my-model: https://example.org/my-model#
          onz-g: http://purl.org/ozo/onz-g#
          skos: http://www.w3.org/2004/02/skos/core#
          semapv: https://w3id.org/semapv/vocab/
          orcid: https://orcid.org/
        ontologies:
          subject: my-model
          object: onz-g
    ```

    Every prefix used in the CSV must be in `curie_map`, and every namespace must end with `/` or `#`.
    Leave out `ontologies` when one side has no ontology source, and then validate without `--check-references`.

4. Fetch both ontologies, then validate, build, and report.

    ```shell
    uv run rosetta ontology fetch my-model
    uv run rosetta ontology fetch onz-g
    uv run rosetta mapping validate my-set --check-references
    uv run rosetta mapping build my-set --output-dir registry/data/mappings/my-set --check-references
    uv run rosetta mapping report my-set --output-dir registry/data/mappings/my-set
    ```

    Each validation issue names the CSV row and column to edit.

## Checklist

- [ ] The source is pinned to a version, and its checksum is recorded.
- [ ] New code has tests with synthetic data, and `uv run tara check` passes.
- [ ] The mapping set validates with `--check-references`, or the missing check is stated.
- [ ] The mapping set has a permanent `mapping_set_id` and a licence.
- [ ] The new source is listed in the [capability matrix](../development/capability-matrix.md).
- [ ] No licensed release data or generated output is committed.
