"""Vocabulary release ingestion use cases."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from plugin_rosetta.reports import IssueSeverity, ValidationIssue, ValidationReport
from plugin_rosetta.vocabulary.adapters import build_output_paths, get_build_adapter
from plugin_rosetta.vocabulary.config import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract, validate_release_frame
from plugin_rosetta.vocabulary.ingest import DEFAULT_CACHE_DIR, cache_dir_for, find_file, ingest_zip
from plugin_rosetta.vocabulary.merge import merge_turtle_files

if TYPE_CHECKING:
    from plugin_rosetta.vocabulary.config import VocabularySource

DEFAULT_VOCABULARY_CONFIG = Path("registry/config/vocabulary-sources.yaml")
"""Default location of the vocabulary source configuration, relative to the workspace root."""
DEFAULT_VOCABULARY_OUTPUT_DIR = Path("registry/data/vocabulary-graphs")
"""Default directory for built vocabulary graphs, relative to the workspace root."""


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
    """Ingest a local vocabulary release ZIP into its versioned cache.

    The release is extracted to `<cache_dir>/<name>/<version>/`. The ZIP is
    checked against the pinned `checksum`, unsafe archive members are rejected,
    the `format_version` marker is checked, and every configured table is
    located and validated against its contract. Error-severity contract
    violations abort the ingest. An integrity manifest is written to
    `.rosetta-release.json`.

    If the release is already cached and `force` is false, nothing is extracted.
    The cached files are verified against the manifest and the tables are
    validated again. The ZIP is then only needed when a checksum is pinned.

    Args:
        name: Name of the vocabulary source.
        zip_path: Path to the release ZIP.
        config_path: Path to `vocabulary-sources.yaml`.
        cache_dir: Root directory of the release cache.
        force: Whether to extract again even if the release is cached.

    Returns:
        The cached release directory and a report. The report can contain
        `vocabulary.missing-checksum` and `vocabulary.unversioned-release`
        warnings and non-fatal contract findings.

    Raises:
        ConfigurationError: If the configuration or a table contract is
            invalid, or `name` is not configured.
        VocabularyChecksumError: If the ZIP or cached files fail the pinned
            checksum or integrity manifest.
        VocabularyIngestError: If the ZIP is missing or invalid, has an unsafe
            member or no format marker, cannot be extracted, or a table cannot
            be located or fails its contract.
    """
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
    """Build an OMOP Turtle graph and provenance sidecar from an ingested release.

    Uses the `omop` source and its `concept`, `concept-relationship`, and
    `relationship` table roles.

    Args:
        release_dir: Directory of an ingested Athena release.
        output_dir: Directory for `omop.ttl` and `omop.meta.json`.
        config_path: Path to `vocabulary-sources.yaml`.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ConfigurationError: If the configuration or a table contract is
            invalid, or the source is not configured.
        VocabularyError: If the release is missing, a table role is not
            configured, or a table cannot be located unambiguously.
        ValidationError: If a release table violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
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
    """Build a DHD thesaurus graph and provenance sidecar from an ingested release.

    Uses the `dhd-thesauri` source. The release must contain exactly one
    `thesauri/DT/*_<format_version>` or `thesauri/VT/*_<format_version>`
    directory. Only concepts and terms active on `as_of` are included.

    Args:
        release_dir: Directory of an ingested DHD thesaurus release.
        output_dir: Directory for `dhd-diagnosethesaurus.ttl` or
            `dhd-verrichtingenthesaurus.ttl` and its sidecar.
        thesaurus: `dt` (Diagnosethesaurus) or `vt` (Verrichtingenthesaurus).
        as_of: Reference date in `YYYYMMDD` form; recorded in the sidecar.
        config_path: Path to `vocabulary-sources.yaml`.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ValueError: If `thesaurus` is not `dt` or `vt`.
        ConfigurationError: If the configuration or a table contract is
            invalid, or the source is not configured.
        VocabularyError: If `format_version` is not configured, the release
            directory is not found, a table role is not configured, or a table
            cannot be located unambiguously.
        ValidationError: If `as_of` is not a valid date or a release table
            violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
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
    """Build OMOP artifacts from the cached release of the configured `omop` version.

    Same as `build_omop_graph` on the cache directory. The release must have
    been ingested with `ingest_release`.

    Args:
        output_dir: Directory for `omop.ttl` and `omop.meta.json`.
        config_path: Path to `vocabulary-sources.yaml`.
        cache_dir: Root directory of the release cache.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ConfigurationError: If the configuration or a table contract is
            invalid, or the source is not configured.
        VocabularyError: If the release is not ingested, a table role is not
            configured, or a table cannot be located unambiguously.
        ValidationError: If a release table violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
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
    """Build DHD artifacts from the cached release of the configured `dhd-thesauri` version.

    Same as `build_dhd_graph` on the cache directory. The release must have
    been ingested with `ingest_release`.

    Args:
        thesaurus: `dt` (Diagnosethesaurus) or `vt` (Verrichtingenthesaurus).
        as_of: Reference date in `YYYYMMDD` form; see `build_dhd_graph`.
        output_dir: Directory for the graph and its sidecar.
        config_path: Path to `vocabulary-sources.yaml`.
        cache_dir: Root directory of the release cache.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ValueError: If `thesaurus` is not `dt` or `vt`.
        ConfigurationError: If the configuration or a table contract is invalid.
        VocabularyError: If the release is missing or incomplete; see `build_dhd_graph`.
        ValidationError: If `as_of` is not a valid date or a release table
            violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
    source = load_vocabulary_sources(config_path).get("dhd-thesauri")
    return build_dhd_graph(
        cache_dir_for(source, cache_dir),
        output_dir,
        thesaurus,
        as_of=as_of,
        config_path=config_path,
    )


def build_cached_rf2_graph(
    name: str,
    output_dir: Path = DEFAULT_VOCABULARY_OUTPUT_DIR,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Path, Path]:
    """Build an RF2 graph from the cached release of the configured version of `name`.

    Same as `build_rf2_graph` on the cache directory. The release must have
    been ingested with `ingest_release`.

    Args:
        name: RF2 source name: `loinc-snomed` or `snomed-international`.
        output_dir: Directory for `<name>.ttl` and `<name>.meta.json`.
        config_path: Path to `vocabulary-sources.yaml`.
        cache_dir: Root directory of the release cache.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ValueError: If no build adapter is registered under `name`.
        ConfigurationError: If the configuration or a table contract is
            invalid, or `name` is not configured.
        VocabularyError: If `language_refset_id` or a table role is not
            configured, or a table cannot be located unambiguously.
        ValidationError: If a release table violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
    source = load_vocabulary_sources(config_path).get(name)
    return get_build_adapter(name).build(
        cache_dir_for(source, cache_dir),
        output_dir,
        config_path=config_path,
        as_of=None,
    )


def build_rf2_graph(
    release_dir: Path,
    output_dir: Path,
    name: str,
    *,
    config_path: Path = DEFAULT_VOCABULARY_CONFIG,
) -> tuple[Path, Path]:
    """Build an RF2 graph from an ingested release.

    Uses the `concept`, `description`, `language`, and `relationship` table
    roles. Preferred terms are selected with `language_refset_id`.

    Args:
        release_dir: Directory of an ingested RF2 release.
        output_dir: Directory for `<name>.ttl` and `<name>.meta.json`.
        name: RF2 source name: `loinc-snomed` or `snomed-international`.
        config_path: Path to `vocabulary-sources.yaml`.

    Returns:
        The paths of the Turtle graph and its JSON provenance sidecar.

    Raises:
        ValueError: If no build adapter is registered under `name`.
        ConfigurationError: If the configuration or a table contract is
            invalid, or `name` is not configured.
        VocabularyError: If `language_refset_id` or a table role is not
            configured, or a table cannot be located unambiguously.
        ValidationError: If a release table violates its contract.
        RosettaIOError: If an output file cannot be written.
    """
    return get_build_adapter(name).build(
        release_dir,
        output_dir,
        config_path=config_path,
        as_of=None,
    )


def merge_built_vocabulary_graphs(
    output_dir: Path = DEFAULT_VOCABULARY_OUTPUT_DIR,
) -> Path:
    """Merge the built graphs of all build adapters into one Turtle graph.

    The merged graph is the set union of the triples. Every graph must have
    been built into `output_dir` first.

    Args:
        output_dir: Directory of the built graphs. `vocabularies.ttl` is
            written to the same directory.

    Returns:
        The path of `vocabularies.ttl`.

    Raises:
        VocabularyError: If an expected graph file does not exist.
        RosettaIOError: If the graphs cannot be read, merged, or written.
    """
    return merge_turtle_files(
        list(build_output_paths(output_dir)),
        output_dir / "vocabularies.ttl",
    )
