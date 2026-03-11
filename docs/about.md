# About

## What is plugin-rosetta?

plugin-rosetta is a Python library for translating [FHIR R4](https://hl7.org/fhir/R4/)
clinical data into [OMOP CDM 5.4](https://ohdsi.github.io/CommonDataModel/) format.
It is part of the [plugin-healthcare](https://github.com/plugin-healthcare) ecosystem —
a suite of composable, open-source data integration components for healthcare data
engineering.

The name "rosetta" refers to the Rosetta Stone — the artefact that made it possible
to translate between previously incompatible writing systems. plugin-rosetta plays
an analogous role: it provides a transparent, standards-grounded translation layer
between the two dominant healthcare data models in use today.

---

## Design principles

**Grounded in authoritative sources.** OMOP schemas are generated directly from the
[OHDSI CommonDataModel](https://github.com/OHDSI/CommonDataModel) CSV definitions.
FHIR-to-OMOP field mappings are derived from the
[HL7 FHIR-OMOP Implementation Guide](https://build.fhir.org/ig/HL7/fhir-omop-ig/)
FML structure maps. Neither model is interpreted ad hoc.

**Transparent and auditable.** Both data models are expressed as
[LinkML](https://linkml.io/) schemas. The `exact_mappings` annotations in
`fhir_resources.yaml` are machine-readable and link every mapped FHIR field to its
OMOP counterpart. Data stewards can inspect the mappings directly in the schema
files or on the [Mappings](mappings.md) page.

**No black-box mapping framework.** Translations are implemented as plain Python
classes — one per FHIR resource — with no intermediate mapping DSL. The code is
straightforward to read, test, and extend.

**Three-layer validation.** Output is validated at the columnar level (nyctea +
Polars), the record level (Pydantic v2), and the semantic level (LinkML `validate()`).

---

## Source pins

| Upstream source | Version |
|----------------|---------|
| [OHDSI CommonDataModel](https://github.com/OHDSI/CommonDataModel) | tag `v5.4.2` |
| [HL7 fhir-omop-ig](https://github.com/HL7/fhir-omop-ig) | tag `1.0.0-ballot` |
| [nyctea](https://github.com/yannick-vinkesteijn/nyctea) | commit `6b113f1` |

---

## Contributing

Contributions are welcome. Please open an issue or pull request on
[GitHub](https://github.com/plugin-healthcare/plugin-rosetta).

See [CONTRIBUTING.md](https://github.com/plugin-healthcare/plugin-rosetta/blob/main/CONTRIBUTING.md)
for guidelines.

---

## License

plugin-rosetta is released under the [MIT License](https://github.com/plugin-healthcare/plugin-rosetta/blob/main/LICENSE).
