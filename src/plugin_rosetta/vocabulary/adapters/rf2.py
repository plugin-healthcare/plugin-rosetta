"""Read RF2 tables and build lightweight SNOMED graphs."""

from typing import TYPE_CHECKING

import polars as pl
from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.reports import IssueSeverity
from plugin_rosetta.vocabulary.frames import validate_release_frame
from plugin_rosetta.vocabulary.namespaces import PREFIX_MAP, sct_iri

if TYPE_CHECKING:
    from pathlib import Path

    from plugin_rosetta.vocabulary.config import ReleaseTable
    from plugin_rosetta.vocabulary.frames import TableContract

IS_A_TYPE_ID = "116680003"
SYNONYM_TYPE_ID = "900000000000013009"
PREFERRED_ACCEPTABILITY_ID = "900000000000548007"


def read_rf2(path: Path, table: ReleaseTable, contract: TableContract) -> pl.DataFrame:
    """Read and validate an RF2 table with configured delimiter settings."""
    frame = pl.scan_csv(
        path,
        separator=table.separator,
        quote_char=table.quote_char,
        infer_schema=False,
    )
    report = validate_release_frame(frame, contract, source_path=path)
    if not report.is_valid:
        messages = "; ".join(issue.message for issue in report.issues if issue.severity is IssueSeverity.ERROR)
        raise ValidationError(f"Vocabulary table {path} is invalid: {messages}")
    return frame.collect()


def active_rows(frame: pl.DataFrame) -> pl.DataFrame:
    """Keep only active RF2 component versions."""
    return frame.filter(pl.col("active") == "1")


def isa_edges(relationships: pl.DataFrame) -> pl.DataFrame:
    """Return active child-to-parent is-a edges."""
    return active_rows(relationships).filter(pl.col("typeId") == IS_A_TYPE_ID).select("sourceId", "destinationId")


def _preferred_description_ids(language: pl.DataFrame, language_refset_id: str) -> pl.DataFrame:
    return (
        active_rows(language)
        .filter((pl.col("refsetId") == language_refset_id) & (pl.col("acceptabilityId") == PREFERRED_ACCEPTABILITY_ID))
        .select("referencedComponentId")
        .unique()
    )


def preferred_terms(
    descriptions: pl.DataFrame,
    language: pl.DataFrame,
    language_refset_id: str,
) -> pl.DataFrame:
    """Return preferred synonym descriptions for one configured dialect."""
    return (
        active_rows(descriptions)
        .filter(pl.col("typeId") == SYNONYM_TYPE_ID)
        .join(
            _preferred_description_ids(language, language_refset_id),
            left_on="id",
            right_on="referencedComponentId",
            how="inner",
        )
        .select("conceptId", "term", pl.col("languageCode").alias("lang"))
    )


def synonyms(
    descriptions: pl.DataFrame,
    language: pl.DataFrame,
    language_refset_id: str,
) -> pl.DataFrame:
    """Return active non-preferred synonym descriptions."""
    return (
        active_rows(descriptions)
        .filter(pl.col("typeId") == SYNONYM_TYPE_ID)
        .join(
            _preferred_description_ids(language, language_refset_id),
            left_on="id",
            right_on="referencedComponentId",
            how="anti",
        )
        .select("conceptId", "term", pl.col("languageCode").alias("lang"))
    )


def build_graph(
    concepts: pl.DataFrame,
    descriptions: pl.DataFrame,
    language: pl.DataFrame,
    relationships: pl.DataFrame,
    language_refset_id: str,
) -> Graph:
    """Build a lightweight SKOS, RDFS, and OWL graph from RF2 frames."""
    graph = Graph()
    for prefix, namespace in PREFIX_MAP.items():
        graph.bind(prefix, namespace)
    graph.bind("skos", SKOS)
    graph.bind("owl", OWL)

    for row in active_rows(concepts).iter_rows(named=True):
        subject = sct_iri(row["id"])
        graph.add((subject, RDF.type, SKOS.Concept))
        graph.add((subject, RDF.type, OWL.Class))
    for row in preferred_terms(descriptions, language, language_refset_id).iter_rows(named=True):
        subject = sct_iri(row["conceptId"])
        label = Literal(row["term"], lang=row["lang"])
        graph.add((subject, SKOS.prefLabel, label))
        graph.add((subject, RDFS.label, label))
    for row in synonyms(descriptions, language, language_refset_id).iter_rows(named=True):
        graph.add((sct_iri(row["conceptId"]), SKOS.altLabel, Literal(row["term"], lang=row["lang"])))
    for row in isa_edges(relationships).iter_rows(named=True):
        child = sct_iri(row["sourceId"])
        parent = sct_iri(row["destinationId"])
        graph.add((child, RDFS.subClassOf, parent))
        graph.add((child, SKOS.broadMatch, parent))
    return graph


def omission_counts(
    concepts: pl.DataFrame,
    descriptions: pl.DataFrame,
    language: pl.DataFrame,
    relationships: pl.DataFrame,
    language_refset_id: str,
) -> dict[str, dict[str, int]]:
    """Count optional RF2 graph values absent from active concepts."""
    concept_ids = set(active_rows(concepts)["id"])
    labels = set(preferred_terms(descriptions, language, language_refset_id)["conceptId"])
    alternatives = set(synonyms(descriptions, language, language_refset_id)["conceptId"])
    children = set(isa_edges(relationships)["sourceId"])
    return {
        "Rf2Concept": {
            "preferred_label": len(concept_ids - labels),
            "alternative_label": len(concept_ids - alternatives),
            "parent": len(concept_ids - children),
        }
    }
