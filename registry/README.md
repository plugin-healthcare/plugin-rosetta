# Local registry

This directory is the first local registry for Rosetta configuration, schemas, mappings, and data.

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
