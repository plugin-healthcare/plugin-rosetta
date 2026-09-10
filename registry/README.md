# Local registry

This directory is the healthcare project's local registry for Rosetta configuration, schemas,
mappings, and data. It is example input for the reusable library, not package data required at
runtime.

An installed package creates an empty layout with `rosetta init <workspace>`. Users supply the
catalogues, schemas, and mappings needed by their own project.

Configuration, schemas, and mappings are tracked so the current setup remains reviewable and reproducible.

Raw source downloads, licensed content, caches, and generated outputs belong under `data/` and are not tracked.

`config/mapping-sets.yaml` preserves mapping-set identifiers, licences, file references, and CURIE maps that previously lived in the `sssom-rosetta` `justfile`.

The `omop-onz-g` mapping-set identifier still points to the legacy `sssom-rosetta` build URL so migration does not silently change artifact identity.

The authored `author_label` values are also retained unchanged even though the contributor table identifies the individual author.

Both values require a separate curator-reviewed correction before publication from `plugin-rosetta`.

The SSSOM Pydantic model is generated from the pinned `sssom-schema==1.1.0a5` source and must not be edited by hand.

Regenerate it with:

```shell
uv run gen-pydantic --extra-fields forbid --emptylist-for-multivalued-slots .venv/lib/python3.14/site-packages/sssom_schema/schema/sssom_schema.yaml > src/plugin_rosetta/mapping/models/sssom.py
```

```text
registry/
  config/    # source definitions and pipeline configuration
  schemas/   # validation and artifact schemas
  mappings/  # authored mapping content and metadata
  data/      # local raw, cached, and generated payloads
```

Portable artifacts remain in their original open formats and must not require Rosetta to read or use them.

`rosetta mapping build` writes deterministic SSSOM/TSV and RDF/Turtle files under `registry/data/`.

`rosetta mapping report` writes Markdown and standalone HTML reports beside those artifacts.

`config/ontology-sources.yaml` pins each ontology source's version, canonical IRI, and download URL, migrated unchanged from `sssom-rosetta`'s `ontology/sources.py`. Checksums are left unset until a curator confirms the downloaded bytes and backfills them as a reviewed change.

`rosetta ontology fetch <name>` downloads (or reuses a cached copy of) a configured source into `registry/data/ontologies/<name>/<version>/ontology.ttl`. Use `--force` to re-download and `just fetch` to fetch both configured sources.

## Vocabulary releases

`config/vocabulary-sources.yaml` records the four migrated licence-gated sources, their pinned release
and format versions, and the page from which a curator obtains each ZIP. Rosetta never downloads these
releases.

Ingest a manually downloaded release with:

```shell
uv run rosetta vocabulary ingest <name> <release.zip>
```

The command verifies the configured SHA-256 when present, rejects unsafe archive paths, locates every
required table declared for the source, and applies its tracked table contract before promoting the
extracted directory into the cache. Releases are cached under `data/vocabularies/<name>/<version>/`
with a manifest containing the archive digest and extracted-file digests. For a source with a pinned
checksum, repeated ingest requires the original ZIP and verifies cached files against that trusted
artifact rather than trusting the writable manifest. An unpinned source can be reused without the
ZIP; its manifest detects accidental corruption but is not an authentication boundary. Repeated
ingest also revalidates the tables and reuses the directory unless `--force` is set. When no checksum
is pinned, the command prints the computed digest on every run so it can be reviewed and added to the
source catalogue.

Contracts under `schemas/vocabularies/` declare the required columns, data types, and nullability for
the Athena, DHD, and RF2 tables used by later graph builders. Extra columns are retained and reported
as informational findings, while missing columns, incompatible types, and nulls in required columns
are errors.

The source catalogue owns required-table lookup and reader settings. Each table has a stable
semantic `role`; its physical `name`, `prefix`, `suffix`, and path fragment remain configurable.
Vocabulary adapters select roles rather than defining filenames, separators, or quote behavior.

## OMOP vocabulary graph

Run `rosetta vocabulary build-omop` after ingesting an Athena release. The graph uses
`https://w3id.org/omop/concept/<concept_id>` for OMOP concept nodes. It links SNOMED CT, LOINC,
RxNorm, ICD-10, and ICD-10-CM concepts to their percent-encoded native code IRIs with
`skos:exactMatch`; RxNorm Extension concepts remain OMOP-only because no native namespace exists.

OMOP relationship rows retain their source semantics. Each edge uses the corresponding
`relationship_concept_id` as an OMOP predicate IRI, and each used predicate receives the
`relationship_name` as an English `skos:prefLabel`. The builder does not collapse these
relationships into selected SKOS predicates or label unused relationship types.

The deterministic `data/vocabulary-graphs/omop.ttl` output is accompanied by `omop.meta.json`,
which records the configured source name, source version, format version, and UTC build time.

## DHD thesaurus graphs

Run both DHD builders after ingesting `dhd-thesauri`, passing the date whose active state should be
materialized:

```shell
uv run rosetta vocabulary build-dhd-diagnosethesaurus --as-of 20260910
uv run rosetta vocabulary build-dhd-verrichtingenthesaurus --as-of 20260910
```

Diagnosis concepts use `https://w3id.org/dhd/diagnosethesaurus/concept/<ConceptID>` and procedure
concepts use `https://w3id.org/dhd/verrichtingenthesaurus/concept/<ConceptID>`, preventing collisions
when both releases reuse an identifier. Dutch FSN labels are preferred over English labels.

DBC diagnosis identifiers are only unique within a specialty. The graph therefore mints
`https://w3id.org/dhd/dbc/<SpecialismeCode>-<DBC_ID>` and never uses a raw `DBC_ID`. DT outputs link
to SNOMED CT with `skos:exactMatch` and to ICD-10 and DBC with `skos:closeMatch`; VT outputs contain
SNOMED CT links only. A blank end date remains active, and each sidecar records the explicit
`as_of` date.
