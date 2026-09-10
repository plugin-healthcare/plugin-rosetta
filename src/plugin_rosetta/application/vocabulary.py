"""Vocabulary release ingestion use cases."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from plugin_rosetta.config.vocabulary_sources import load_vocabulary_sources
from plugin_rosetta.core.report import ValidationReport
from plugin_rosetta.vocabulary.frames import load_table_contract, validate_release_frame
from plugin_rosetta.vocabulary.ingest import DEFAULT_CACHE_DIR, find_file, ingest_zip

if TYPE_CHECKING:
    from plugin_rosetta.config.vocabulary_sources import VocabularySource

DEFAULT_VOCABULARY_CONFIG = Path("registry/config/vocabulary-sources.yaml")


def _validate_release_tables(
    release_dir: Path,
    source: VocabularySource,
    registry_root: Path,
) -> ValidationReport:
    report = ValidationReport()
    for table in source.tables:
        table_path = find_file(
            release_dir,
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
    return result.path, checksum_report.merge(result.validation_report)
