# Background

Rosetta reads hand-written mappings and licensed terminology releases from a registry and writes open files.
Each library feature has a matching group of CLI commands, as decided in [ADR-0002](../decisions/0002-organize-the-library-around-public-feature-apis.md).

```mermaid
flowchart LR
    subgraph registry["Registry, owned by the project"]
        ms["Mapping sets<br/>CSV + CSVW"]
        os["Ontology sources<br/>OMOP CDM, ONZ-G"]
        vs["Vocabulary sources<br/>SNOMED CT, LOINC, DHD"]
    end
    subgraph library["Library and CLI"]
        mapping["mapping"]
        ontology["ontology"]
        vocabulary["vocabulary"]
        artifacts["artifacts"]
    end
    subgraph outputs["Open outputs in registry/data/"]
        sssom["SSSOM/TSV, RDF/Turtle,<br/>Markdown and HTML reports"]
        graphs["Vocabulary graphs<br/>+ provenance JSON"]
        catalogue["Versioned artifact catalogue"]
    end
    ms --> mapping
    os --> ontology --> mapping
    vs --> vocabulary
    mapping --> sssom
    vocabulary --> graphs
    sssom & graphs --> artifacts --> catalogue
```

Validation never downloads anything, and a build writes no file when validation finds an error.

| Page | Description |
| --- | --- |
| [From Your Standard to Rosetta](from-standard-to-rosetta.md) | What Rosetta does with OMOP, ONZ-G, the DHD thesauri, SNOMED CT, LOINC, and FHIR. |
| [Registry](registry.md) | What belongs in a registry and what belongs in the library. |
