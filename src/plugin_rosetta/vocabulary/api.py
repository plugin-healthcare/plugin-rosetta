"""Vocabulary release ingestion use cases."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport
from plugin_rosetta.vocabulary.adapters import get_build_adapter
from plugin_rosetta.vocabulary.config import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract, validate_release_frame
from plugin_rosetta.vocabulary.ingest import DEFAULT_CACHE_DIR, cache_dir_for, find_file, ingest_zip

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary.config import VocabularySource

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


def build_omop_graph(
    release_dir: Path,
    output_dir: Path,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
) -> tuple[Path, Path]:
    """Build an OMOP Turtle graph and provenance from an ingested release."""
    return get_build_adapter("omop").build(
        release_dir,
        output_dir,
        config_path=config_path,
        as_of=None,
    )


def build_dhd_graph(
    release_dir: Path,
    output_dir: Path,
    thesaurus: str,
    *,
    as_of: str,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
) -> tuple[Path, Path]:
    """Build a DHD thesaurus graph and provenance from an ingested release."""
    target = {
        "dt": "dhd-diagnosethesaurus",
        "vt": "dhd-verrichtingenthesaurus",
    }.get(thesaurus)
    if target is None:
        raise ValueError(f"Unknown DHD thesaurus {thesaurus!r}. Known values: dt, vt")
    return get_build_adapter(target).build(
        release_dir,
        output_dir,
        config_path=config_path,
        as_of=as_of,
    )


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


def build_cached_dhd_graph(
    thesaurus: str,
    *,
    as_of: str,
    output_dir: Path = DEFAULT_VOCABULARY_OUTPUT_DIR,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Path, Path]:
    """Build DHD artifacts from the configured versioned release cache."""
    source = load_vocabulary_sources(config_path).get("dhd-thesauri")
    return build_dhd_graph(
        cache_dir_for(source, cache_dir),
        output_dir,
        thesaurus,
        as_of=as_of,
        config_path=config_path,
    )
