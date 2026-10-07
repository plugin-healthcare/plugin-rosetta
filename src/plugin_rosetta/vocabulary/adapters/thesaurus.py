"""Adapt configured diagnosis and procedure thesaurus release tables."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Literal, NamedTuple

import polars as pl
from maplib import Model

from plugin_rosetta.errors import ValidationError, VocabularyError
from plugin_rosetta.reports import IssueSeverity
from plugin_rosetta.vocabulary.frames import validate_release_frame
from plugin_rosetta.vocabulary.ingest import find_file
from plugin_rosetta.vocabulary.namespaces import DBC, ICD10, PREFIX_MAP, SCT, THESAURUS_NAMESPACES
from plugin_rosetta.vocabulary.templates import (
    DHD_CLOSE_MATCH_TEMPLATE,
    DHD_CLOSE_MATCH_TEMPLATE_IRI,
    DHD_CONCEPT_TEMPLATE,
    DHD_CONCEPT_TEMPLATE_IRI,
    LANG_STRING_FIELD,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from plugin_rosetta.vocabulary.config import ReleaseTable, VocabularySource
    from plugin_rosetta.vocabulary.frames import TableContract

type Thesaurus = Literal["dt", "vt"]

_SKOS = "http://www.w3.org/2004/02/skos/core#"
_PREFIXES = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {"skos": _SKOS}


class DhdCrossLinks(NamedTuple):
    """Optional DT-only derivation frames."""

    icd10: pl.DataFrame | None = None
    dbc: pl.DataFrame | None = None


def _validate_date(value: str, *, label: str) -> None:
    if re.fullmatch(r"\d{8}", value) is None:
        raise ValidationError(f"{label} must be a valid YYYYMMDD date, found {value!r}")
    try:
        datetime.strptime(value, "%Y%m%d")  # noqa: DTZ007
    except ValueError as error:
        raise ValidationError(f"{label} must be a valid YYYYMMDD date, found {value!r}") from error


def _validated_scan(path: Path, table: ReleaseTable, contract: TableContract) -> pl.LazyFrame:
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
    invalid_dates = (
        frame.select("Begindatum", "Einddatum")
        .unpivot()
        .filter(
            pl.col("value").is_not_null()
            & (pl.col("value") != "")
            & (
                ~pl.col("value").str.contains(r"^\d{8}$")
                | pl.col("value").str.to_date("%Y%m%d", strict=False).is_null()
            )
        )
        .head(1)
        .collect()
    )
    if invalid_dates.height:
        column, value = invalid_dates.row(0)
        raise ValidationError(f"Vocabulary table {path} has invalid {column} value {value!r}; expected YYYYMMDD")
    blank_starts = (
        frame.filter(pl.col("Begindatum").is_null() | (pl.col("Begindatum") == "")).select(pl.len()).collect()
    )
    if blank_starts.item():
        raise ValidationError(f"Vocabulary table {path} contains a blank Begindatum")
    return frame


def _non_blank(column: str) -> pl.Expr:
    return pl.when(pl.col(column).is_not_null() & (pl.col(column) != "")).then(pl.col(column)).otherwise(None)


def _active(frame: pl.LazyFrame, as_of: str) -> pl.LazyFrame:
    _validate_date(as_of, label="as_of")
    end_date = _non_blank("Einddatum")
    return frame.filter((pl.col("Begindatum") <= as_of) & (end_date.is_null() | (end_date >= as_of)))


def load_concepts(
    path: Path,
    table: ReleaseTable,
    contract: TableContract,
    as_of: str,
) -> pl.DataFrame:
    """Load DHD concepts active on the requested date."""
    return _active(_validated_scan(path, table, contract), as_of).select("ConceptID").collect()


def load_snomed_terms(
    path: Path,
    table: ReleaseTable,
    contract: TableContract,
    as_of: str,
) -> pl.DataFrame:
    """Load one active SNOMED identifier per DHD concept."""
    return (
        _active(_validated_scan(path, table, contract), as_of)
        .filter(pl.col("TypeTerm") == "FSN")
        .with_columns(SnomedID=_non_blank("SnomedID"))
        .filter(pl.col("SnomedID").is_not_null())
        .select("ConceptID", "SnomedID")
        .unique()
        .collect()
    )


def load_labels(
    path: Path,
    table: ReleaseTable,
    contract: TableContract,
    as_of: str,
) -> pl.DataFrame:
    """Load one deterministic preferred label, preferring Dutch over English."""
    return (
        _active(_validated_scan(path, table, contract), as_of)
        .filter(pl.col("TypeTerm") == "FSN")
        .with_columns(
            Omschrijving=_non_blank("Omschrijving"),
            Language=_non_blank("TaalCode").str.slice(0, 2).str.to_lowercase(),
        )
        .filter(pl.col("Omschrijving").is_not_null() & pl.col("Language").is_not_null())
        .with_columns(
            _language_rank=pl.when(pl.col("Language") == "nl")
            .then(0)
            .when(pl.col("Language") == "en")
            .then(1)
            .otherwise(2)
        )
        .sort("ConceptID", "_language_rank", "Language", "Omschrijving")
        .unique(subset="ConceptID", keep="first", maintain_order=True)
        .select("ConceptID", "Omschrijving", "Language")
        .collect()
    )


def load_icd10(
    path: Path,
    table: ReleaseTable,
    contract: TableContract,
    as_of: str,
) -> pl.DataFrame:
    """Load all active non-blank ICD-10 derivations."""
    return (
        _active(_validated_scan(path, table, contract), as_of)
        .with_columns(ICD10=_non_blank("ICD10"))
        .filter(pl.col("ICD10").is_not_null())
        .select("ConceptID", "ICD10")
        .collect()
    )


def load_dbc(
    path: Path,
    table: ReleaseTable,
    contract: TableContract,
    as_of: str,
) -> pl.DataFrame:
    """Load active DBC derivations with specialty-scoped identity."""
    return (
        _active(_validated_scan(path, table, contract), as_of)
        .with_columns(DBC_ID=_non_blank("DBC_ID"))
        .filter(pl.col("DBC_ID").is_not_null())
        .select(
            "ConceptID",
            DBC_ID=pl.concat_str("SpecialismeCode", "DBC_ID", separator="-"),
        )
        .collect()
    )


def _concept_rows(
    thesaurus: Thesaurus,
    concepts: pl.DataFrame,
    snomed_terms: pl.DataFrame,
    labels: pl.DataFrame,
) -> pl.DataFrame:
    namespace = THESAURUS_NAMESPACES[thesaurus]
    return (
        concepts.join(snomed_terms, on="ConceptID", how="left")
        .join(labels, on="ConceptID", how="left")
        .with_columns(
            subject=pl.concat_str(pl.lit(str(namespace)), pl.col("ConceptID")),
            snomed=pl.when(pl.col("SnomedID").is_not_null())
            .then(pl.concat_str(pl.lit(str(SCT)), pl.col("SnomedID")))
            .otherwise(None),
            label=pl.when(pl.col("Omschrijving").is_not_null())
            .then(pl.struct(pl.col("Omschrijving").alias(LANG_STRING_FIELD), pl.col("Language").alias("l")))
            .otherwise(None),
        )
    )


def _close_match_rows(
    thesaurus: Thesaurus,
    pairs: pl.DataFrame,
    code_column: str,
    namespace: object,
) -> pl.DataFrame:
    return pairs.with_columns(
        subject=pl.concat_str(pl.lit(str(THESAURUS_NAMESPACES[thesaurus])), pl.col("ConceptID")),
        object=pl.concat_str(pl.lit(str(namespace)), pl.col(code_column)),
    ).select("subject", "object")


def build_graph(
    thesaurus: Thesaurus,
    concepts: pl.DataFrame,
    snomed_terms: pl.DataFrame,
    labels: pl.DataFrame,
    cross_links: DhdCrossLinks | None = None,
) -> Model:
    """Map DHD concepts and derivations into a SKOS graph."""
    model = Model()
    model.add_prefixes(_PREFIXES)
    model.add_template(DHD_CONCEPT_TEMPLATE)
    model.add_template(DHD_CLOSE_MATCH_TEMPLATE)
    rows = _concept_rows(thesaurus, concepts, snomed_terms, labels)
    model.map(DHD_CONCEPT_TEMPLATE_IRI, rows.select("subject", "label", "snomed"))
    if cross_links is not None and cross_links.icd10 is not None and cross_links.icd10.height:
        model.map(
            DHD_CLOSE_MATCH_TEMPLATE_IRI,
            _close_match_rows(thesaurus, cross_links.icd10, "ICD10", ICD10),
        )
    if cross_links is not None and cross_links.dbc is not None and cross_links.dbc.height:
        model.map(
            DHD_CLOSE_MATCH_TEMPLATE_IRI,
            _close_match_rows(thesaurus, cross_links.dbc, "DBC_ID", DBC),
        )
    return model


def _release_directory(root: Path, thesaurus: Thesaurus, format_version: str) -> Path:
    thesaurus_root = root / "thesauri" / thesaurus.upper()
    found = sorted(path for path in thesaurus_root.iterdir() if path.is_dir()) if thesaurus_root.is_dir() else []
    matches = [path for path in found if path.name.endswith(f"_{format_version}")]
    if len(matches) != 1:
        found_text = ", ".join(str(path) for path in found) or "none"
        raise VocabularyError(
            f"Expected exactly one {thesaurus.upper()} release directory ending in "
            f"'_{format_version}' under {root}; found: {found_text}"
        )
    return matches[0]


def _table(source: VocabularySource, role: str) -> ReleaseTable:
    try:
        return next(table for table in source.tables if table.role == role)
    except StopIteration as error:
        raise VocabularyError(f"Vocabulary source {source.name!r} has no table role {role!r}") from error


def _load(
    release_dir: Path,
    source: VocabularySource,
    registry_root: Path,
    role: str,
    as_of: str,
    loader: Callable[[Path, ReleaseTable, TableContract, str], pl.DataFrame],
) -> pl.DataFrame:
    from plugin_rosetta.vocabulary.frames import load_table_contract

    table = _table(source, role)
    path = find_file(
        release_dir,
        name=table.name,
        prefix=table.prefix,
        suffix=table.suffix,
        contains=table.contains,
    )
    return loader(path, table, load_table_contract(registry_root / table.contract), as_of)


def build_from_release(
    release_root: Path,
    thesaurus: Thesaurus,
    source: VocabularySource,
    registry_root: Path,
    *,
    as_of: str,
) -> Model:
    """Build one DHD graph from a configured ingested release."""
    if source.format_version is None:
        raise VocabularyError(f"Vocabulary source {source.name!r} has no configured format version")
    _release_directory(release_root, thesaurus, source.format_version)
    concepts = _load(
        release_root,
        source,
        registry_root,
        f"{thesaurus}-concept",
        as_of,
        load_concepts,
    )
    snomed = _load(
        release_root,
        source,
        registry_root,
        f"{thesaurus}-term",
        as_of,
        load_snomed_terms,
    )
    labels = _load(
        release_root,
        source,
        registry_root,
        f"{thesaurus}-term",
        as_of,
        load_labels,
    )
    if thesaurus == "vt":
        return build_graph(thesaurus, concepts, snomed, labels)
    icd10 = _load(
        release_root,
        source,
        registry_root,
        "dt-icd10",
        as_of,
        load_icd10,
    )
    dbc = _load(
        release_root,
        source,
        registry_root,
        "dt-dbc",
        as_of,
        load_dbc,
    )
    return build_graph(thesaurus, concepts, snomed, labels, DhdCrossLinks(icd10, dbc))
