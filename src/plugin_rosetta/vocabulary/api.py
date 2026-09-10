"""Vocabulary release ingestion use cases."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from plugin_rosetta.errors import ConfigurationError, VocabularyError
from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport
from plugin_rosetta.vocabulary._graph_io import write_turtle
from plugin_rosetta.vocabulary.config import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract, validate_release_frame
from plugin_rosetta.vocabulary.ingest import DEFAULT_CACHE_DIR, cache_dir_for, find_file, ingest_zip
from plugin_rosetta.vocabulary.namespaces import PREFIX_MAP
from plugin_rosetta.vocabulary.omop import (
    build_graph,
    load_relationship_types,
    load_relationships,
    load_target_concepts,
)
from plugin_rosetta.vocabulary.provenance import write_provenance

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary.config import ReleaseTable, VocabularySource

DEFAULT_VOCABULARY_CONFIG = Path("registry/config/vocabulary-sources.yaml")
DEFAULT_VOCABULARY_OUTPUT_DIR = Path("registry/data/vocabulary-graphs")


def _validate_release_tables(
    release_dir: Path,
    source: VocabularySource,
    registry_root: Path,
) -> ValidationReport:
    report = ValidationReport()
    for table in source.tables:
        table_path = find_file(
            release_dir,
            name=table.name,
            prefix=table.prefix,
            suffix=table.suffix,
            contains=table.contains,
        )
        frame = pl.scan_csv(
            table_path,
            separator=table.separator,
            quote_char=table.quote_char,
            infer_schema=False,
        )
        contract = load_table_contract(registry_root / table.contract)
        report = report.merge(validate_release_frame(frame, contract, source_path=table_path))
    return report


def ingest_release(
    name: str,
    zip_path: Path,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
) -> tuple[Path, ValidationReport]:
    """Ingest a configured local vocabulary release into its versioned cache."""
    source = load_vocabulary_sources(config_path).get(name)
    registry_root = config_path.parent.parent
    result = ingest_zip(
        source,
        zip_path,
        cache_dir=cache_dir,
        force=force,
        validator=lambda release_dir: _validate_release_tables(release_dir, source, registry_root),
    )
    checksum_report = ValidationReport(issues=(result.issue,)) if result.issue is not None else ValidationReport()
    version_report = (
        ValidationReport(
            issues=(
                ValidationIssue(
                    code="vocabulary.unversioned-release",
                    severity=IssueSeverity.WARNING,
                    location=source.name,
                    message=(
                        f"Vocabulary source {source.name!r} version is 'unversioned'; "
                        "pin the curator-confirmed release before publication."
                    ),
                ),
            )
        )
        if source.version == "unversioned"
        else ValidationReport()
    )
    return result.path, checksum_report.merge(version_report, result.validation_report)


def _required_table(source: VocabularySource, name: str) -> ReleaseTable:
    try:
        return next(table for table in source.tables if table.name == name)
    except StopIteration as error:
        raise ConfigurationError(f"Vocabulary source {source.name!r} has no required table named {name!r}") from error


def build_omop_graph(
    release_dir: Path,
    output_dir: Path,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
) -> tuple[Path, Path]:
    """Build an OMOP Turtle graph and provenance from an ingested release."""
    source = load_vocabulary_sources(config_path).get("omop")
    if not release_dir.is_dir() or not any(path.is_file() for path in release_dir.rglob("*")):
        raise VocabularyError(
            f"No ingested OMOP release at {release_dir}. Run 'rosetta vocabulary ingest omop <zip>' first."
        )
    registry_root = config_path.parent.parent
    concept_table = _required_table(source, "CONCEPT.csv")
    relationship_table = _required_table(source, "CONCEPT_RELATIONSHIP.csv")
    relationship_type_table = _required_table(source, "RELATIONSHIP.csv")

    concepts = load_target_concepts(
        find_file(release_dir, name=concept_table.name),
        concept_table,
        load_table_contract(registry_root / concept_table.contract),
    )
    relationships = load_relationships(
        find_file(release_dir, name=relationship_table.name),
        relationship_table,
        load_table_contract(registry_root / relationship_table.contract),
        concepts["concept_id"],
    )
    relationship_types = load_relationship_types(
        find_file(release_dir, name=relationship_type_table.name),
        relationship_type_table,
        load_table_contract(registry_root / relationship_type_table.contract),
    )
    model = build_graph(concepts, relationships, relationship_types)
    turtle_path = write_turtle(
        model,
        output_dir / "omop.ttl",
        prefixes={prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()}
        | {"skos": "http://www.w3.org/2004/02/skos/core#"},
    )
    metadata_path = write_provenance(
        turtle_path,
        source_name=source.name,
        source_version=source.version,
        format_version=source.format_version,
    )
    return turtle_path, metadata_path


def build_cached_omop_graph(
    output_dir: Path = DEFAULT_VOCABULARY_OUTPUT_DIR,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Path, Path]:
    """Build OMOP artifacts from the configured versioned release cache."""
    source = load_vocabulary_sources(config_path).get("omop")
    return build_omop_graph(
        cache_dir_for(source, cache_dir),
        output_dir,
        config_path=config_path,
    )
