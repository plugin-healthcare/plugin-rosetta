"""Adapt declared Athena release tables into an OMOP vocabulary graph."""

from typing import TYPE_CHECKING

import polars as pl
from maplib import Model

from plugin_rosetta.errors import ValidationError
from plugin_rosetta.reports import IssueSeverity
from plugin_rosetta.vocabulary.frames import validate_release_frame
from plugin_rosetta.vocabulary.namespaces import OMOP_CONCEPT, PREFIX_MAP, TARGET_VOCABULARIES, source_concept_iri
from plugin_rosetta.vocabulary.templates import CONCEPT_TEMPLATE, CONCEPT_TEMPLATE_IRI, language_tagged_column

if TYPE_CHECKING:
    from pathlib import Path

    from plugin_rosetta.vocabulary.config import ReleaseTable
    from plugin_rosetta.vocabulary.frames import TableContract

_SKOS = "http://www.w3.org/2004/02/skos/core#"
_PREFIXES = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {"skos": _SKOS}


def _validated_scan(path: Path, table: ReleaseTable, contract: TableContract) -> pl.LazyFrame:
    frame = pl.scan_csv(
        path,
        separator=table.separator,
        quote_char=table.quote_char,
        infer_schema=False,
    )
    report = validate_release_frame(frame, contract, source_path=path)
    if report.is_valid:
        return frame
    messages = "; ".join(issue.message for issue in report.issues if issue.severity is IssueSeverity.ERROR)
    if table.quote_char is None and any(issue.code == "vocabulary.null-value" for issue in report.issues):
        messages += (
            "; malformed tab-delimited rows are invalid because embedded newlines cannot be represented "
            "when quote parsing is disabled"
        )
    raise ValidationError(f"Vocabulary table {path} is invalid: {messages}")


def load_target_concepts(
    concept_csv: Path,
    table: ReleaseTable,
    contract: TableContract,
) -> pl.DataFrame:
    """Read and retain only concepts from integrated OMOP vocabularies."""
    return (
        _validated_scan(concept_csv, table, contract)
        .filter(pl.col("vocabulary_id").is_in(list(TARGET_VOCABULARIES)))
        .select("concept_id", "concept_name", "vocabulary_id", "concept_code")
        .collect()
    )


def load_relationships(
    relationship_csv: Path,
    table: ReleaseTable,
    contract: TableContract,
    concept_ids: pl.Series,
) -> pl.DataFrame:
    """Read current relationships whose endpoints are both in scope."""
    wanted = concept_ids.implode()
    return (
        _validated_scan(relationship_csv, table, contract)
        .filter(
            (pl.col("invalid_reason").is_null() | (pl.col("invalid_reason") == ""))
            & pl.col("concept_id_1").is_in(wanted)
            & pl.col("concept_id_2").is_in(wanted)
        )
        .select("concept_id_1", "concept_id_2", "relationship_id")
        .collect()
    )


def load_relationship_types(
    relationship_types_csv: Path,
    table: ReleaseTable,
    contract: TableContract,
) -> pl.DataFrame:
    """Read the OMOP relationship identifier, concept, and label lookup."""
    return (
        _validated_scan(relationship_types_csv, table, contract)
        .select("relationship_id", "relationship_concept_id", "relationship_name")
        .collect()
    )


def _omop_iri_column(column: str) -> pl.Expr:
    return pl.concat_str([pl.lit(str(OMOP_CONCEPT)), pl.col(column)])


def _non_blank(column: str) -> pl.Expr:
    return pl.when(pl.col(column).is_not_null() & (pl.col(column) != "")).then(pl.col(column)).otherwise(None)


def _concept_rows(concepts: pl.DataFrame) -> pl.DataFrame:
    rows = concepts.with_columns(
        subject=_omop_iri_column("concept_id"),
        label=language_tagged_column(concepts.select(_non_blank("concept_name")).to_series()),
        code=_non_blank("concept_code"),
    )
    source_iris = [
        str(iri) if concept_code and (iri := source_concept_iri(vocabulary_id, concept_code)) is not None else None
        for vocabulary_id, concept_code in zip(concepts["vocabulary_id"], concepts["concept_code"], strict=True)
    ]
    return rows.with_columns(source=pl.Series(source_iris, dtype=pl.String))


def _relationship_rows(
    relationships: pl.DataFrame,
    relationship_types: pl.DataFrame,
) -> pl.DataFrame:
    return (
        relationships.join(
            relationship_types.select("relationship_id", "relationship_concept_id"),
            on="relationship_id",
            how="inner",
        )
        .with_columns(
            subject=_omop_iri_column("concept_id_1"),
            predicate=_omop_iri_column("relationship_concept_id"),
            object=_omop_iri_column("concept_id_2"),
        )
        .select("subject", "predicate", "object")
    )


def _relationship_label_rows(
    relationships: pl.DataFrame,
    relationship_types: pl.DataFrame,
) -> pl.DataFrame:
    used_ids = relationships.join(
        relationship_types.select("relationship_id", "relationship_concept_id"),
        on="relationship_id",
        how="inner",
    )["relationship_concept_id"].unique()
    labels = (
        relationship_types.filter(pl.col("relationship_concept_id").is_in(used_ids.implode()))
        .select("relationship_concept_id", "relationship_name")
        .unique()
    )
    return labels.with_columns(
        subject=_omop_iri_column("relationship_concept_id"),
        predicate=pl.lit(f"{_SKOS}prefLabel"),
        object=language_tagged_column(labels["relationship_name"]),
    ).select("subject", "predicate", "object")


def build_graph(
    concepts: pl.DataFrame,
    relationships: pl.DataFrame,
    relationship_types: pl.DataFrame,
) -> Model:
    """Map OMOP concepts and relationships into a SKOS graph."""
    unknown_relationships = sorted(set(relationships["relationship_id"]) - set(relationship_types["relationship_id"]))
    if unknown_relationships:
        raise ValidationError(
            f"OMOP relationship rows have no relationship concept: {', '.join(unknown_relationships)}"
        )
    model = Model()
    model.add_prefixes(_PREFIXES)
    model.add_template(CONCEPT_TEMPLATE)
    model.map(
        CONCEPT_TEMPLATE_IRI,
        _concept_rows(concepts).select("subject", "label", "code", "source"),
    )
    if relationships.height:
        model.map_triples(_relationship_label_rows(relationships, relationship_types))
        model.map_triples(_relationship_rows(relationships, relationship_types))
    return model
