"""OTTR templates used to map vocabulary tables to RDF."""

import polars as pl

LANG_STRING_FIELD = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#langString>"
CONCEPT_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#OmopConceptTemplate"
CONCEPT_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

skos:OmopConceptTemplate [
    ?subject,
    ? ?label,
    ? ?code,
    ? ?source
] :: {
    ottr:Triple(?subject, rdf:type, skos:Concept),
    ottr:Triple(?subject, skos:prefLabel, ?label),
    ottr:Triple(?subject, skos:notation, ?code),
    ottr:Triple(?subject, skos:exactMatch, ?source)
} .
"""

DHD_CONCEPT_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#DhdConceptTemplate"
DHD_CONCEPT_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

skos:DhdConceptTemplate [
    ?subject,
    ? ?label,
    ? ?snomed
] :: {
    ottr:Triple(?subject, rdf:type, skos:Concept),
    ottr:Triple(?subject, skos:prefLabel, ?label),
    ottr:Triple(?subject, skos:exactMatch, ?snomed)
} .
"""

DHD_CLOSE_MATCH_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#DhdCloseMatchTemplate"
DHD_CLOSE_MATCH_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

skos:DhdCloseMatchTemplate [
    ?subject,
    ?object
] :: {
    ottr:Triple(?subject, skos:closeMatch, ?object)
} .
"""


def language_tagged_column(values: pl.Series, language: str = "en") -> pl.Series:
    """Represent strings as Maplib language-tagged literal structs."""
    return (
        pl.DataFrame({"value": values})
        .with_columns(pl.lit(language).alias("language"))
        .select(
            pl.struct(
                [
                    pl.col("value").alias(LANG_STRING_FIELD),
                    pl.col("language").alias("l"),
                ]
            ).alias("literal")
        )
        .to_series()
    )
