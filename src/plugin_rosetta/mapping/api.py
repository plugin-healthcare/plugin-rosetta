"""Mapping use cases: read, validate, build, and report a configured mapping set."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from linkml_runtime.utils.metamodelcore import URI

from plugin_rosetta.errors import ConfigurationError, ValidationError
from plugin_rosetta.mapping.config import load_mapping_sets
from plugin_rosetta.mapping.io.csvw import read_mapping_rows
from plugin_rosetta.mapping.io.rdf import render_turtle
from plugin_rosetta.mapping.io.sssom import render_sssom_tsv
from plugin_rosetta.mapping.models.sssom import MappingSet
from plugin_rosetta.mapping.report import render_html, render_markdown
from plugin_rosetta.mapping.validate import validate_referential_integrity, validate_schema_conformance
from plugin_rosetta.ontology.api import DEFAULT_ONTOLOGY_CONFIG
from plugin_rosetta.ontology.config import load_ontology_sources
from plugin_rosetta.ontology.loader import DEFAULT_CACHE_DIR, load_cached_ontology
from plugin_rosetta.reports import IssueSeverity
from plugin_rosetta.utils.io.atomic import atomic_write_text

if TYPE_CHECKING:
    from rdflib import Graph

    from plugin_rosetta.mapping.config import MappingSetConfig
    from plugin_rosetta.ontology.config import OntologySourcesConfig
    from plugin_rosetta.reports import ValidationReport

DEFAULT_MAPPING_CONFIG = Path("registry/config/mapping-sets.yaml")
"""Default location of the mapping-set configuration, relative to the workspace root."""


@dataclass(frozen=True)
class MappingReadResult:
    """Validated mapping set and the issues found while reading it.

    Attributes:
        mapping_set: The SSSOM `MappingSet`, with one `Mapping` per CSV row.
        report: Findings from reading. Check `report.is_valid` before publishing.
    """

    mapping_set: MappingSet
    report: ValidationReport


def read_mapping_set(
    key: str,
    *,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
    check_references: bool = False,
    ontology_config_path: Path = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> MappingReadResult:
    """Read a configured mapping set, optionally checking it against its ontologies.

    Reading checks the CSV against its CSVW metadata, the primary key, and the
    SSSOM schema; failures raise. With `check_references`, every `subject_id`
    and `object_id` is also looked up in the cached ontology graph it is bound
    to, and unresolved ones are reported as errors. Nothing is downloaded.

    Args:
        key: Key of the mapping set in the configuration.
        config_path: Path to `mapping-sets.yaml`, relative to `root` unless absolute.
        root: Workspace root for relative paths. Defaults to the current directory.
        check_references: Whether to check subjects and objects against the
            bound ontology sources.
        ontology_config_path: Path to `ontology-sources.yaml`, relative to
            `root` unless absolute. Used with `check_references`.
        cache_dir: Ontology cache directory, relative to `root` unless
            absolute. Used with `check_references`.

    Raises:
        ConfigurationError: If a configuration is invalid, `key` is unknown, a
            file is missing, or references are checked without an `ontologies` binding.
        ValidationError: If the CSV violates its CSVW metadata or primary key,
            or a row violates the SSSOM schema.
        RosettaIOError: If a file cannot be read, or a bound ontology is not
            cached, cannot be parsed, or fails its checksum.
    """
    resolved_root = (root or Path.cwd()).resolve()
    ontology_sources = load_ontology_sources(_below(resolved_root, ontology_config_path)) if check_references else None
    config = load_mapping_sets(config_path, root=resolved_root, ontology_sources=ontology_sources).get(key)
    graphs = (
        _bound_graphs(key, config, ontology_sources, _below(resolved_root, cache_dir))
        if ontology_sources is not None
        else None
    )
    rows = read_mapping_rows(
        config.mapping_file_path(resolved_root),
        config.metadata_file_path(resolved_root),
    )
    mapping_set = MappingSet(
        mapping_set_id=URI(config.mapping_set_id),
        license=URI(config.license),
        curie_map=config.curie_map,
        mappings=list(validate_schema_conformance(rows.rows)),
    )
    report = rows.report
    if graphs is not None:
        subject_graph, object_graph = graphs
        report = report.merge(
            validate_referential_integrity(
                mapping_set,
                curie_map=config.curie_map,
                subject_graph=subject_graph,
                object_graph=object_graph,
            )
        )
    return MappingReadResult(mapping_set=mapping_set, report=report)


def build_mapping_artifacts(
    key: str,
    *,
    output_dir: Path,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
    check_references: bool = False,
    ontology_config_path: Path = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Path, Path]:
    """Build portable SSSOM and Turtle artifacts from a valid mapping set.

    The mapping set is read with `read_mapping_set` using the same arguments.
    Nothing is written if the report contains an error. Files are replaced
    atomically.

    Args:
        key: Key of the mapping set in the configuration.
        output_dir: Output directory, created if needed. A relative path is
            resolved against the current directory, not `root`.
        config_path: Path to `mapping-sets.yaml`, relative to `root` unless absolute.
        root: Workspace root for relative paths. Defaults to the current directory.
        check_references: Whether to check references before building.
        ontology_config_path: Path to `ontology-sources.yaml`, relative to
            `root` unless absolute. Used with `check_references`.
        cache_dir: Ontology cache directory, relative to `root` unless
            absolute. Used with `check_references`.

    Returns:
        The paths of `<key>.sssom.tsv` and `<key>.ttl` in `output_dir`.

    Raises:
        ConfigurationError: If the configuration is invalid; see `read_mapping_set`.
        ValidationError: If the mapping set violates CSVW or SSSOM, or its
            report contains errors.
        RosettaIOError: If an input cannot be read or an artifact written.
    """
    result = read_mapping_set(
        key,
        config_path=config_path,
        root=root,
        check_references=check_references,
        ontology_config_path=ontology_config_path,
        cache_dir=cache_dir,
    )
    _refuse_invalid(key, result.report)
    sssom_path = output_dir / f"{key}.sssom.tsv"
    turtle_path = output_dir / f"{key}.ttl"
    sssom = render_sssom_tsv(result.mapping_set)
    turtle = render_turtle(result.mapping_set)
    atomic_write_text(sssom_path, sssom)
    atomic_write_text(turtle_path, turtle)
    return sssom_path, turtle_path


def report_mapping_set(
    key: str,
    *,
    output_dir: Path,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
) -> tuple[Path, Path]:
    """Write portable Markdown and HTML reports.

    The report states the mapping set IRI, the mapping count, and the count per
    predicate. References are not checked.

    Args:
        key: Key of the mapping set in the configuration.
        output_dir: Output directory, created if needed. A relative path is
            resolved against the current directory, not `root`.
        config_path: Path to `mapping-sets.yaml`, relative to `root` unless absolute.
        root: Workspace root for relative paths. Defaults to the current directory.

    Returns:
        The paths of `<key>.md` and `<key>.html` in `output_dir`.

    Raises:
        ConfigurationError: If the configuration is invalid or `key` is unknown.
        ValidationError: If the mapping set violates CSVW or SSSOM.
        RosettaIOError: If an input cannot be read or a report written.
    """
    result = read_mapping_set(key, config_path=config_path, root=root)
    markdown_path = output_dir / f"{key}.md"
    html_path = output_dir / f"{key}.html"
    markdown = render_markdown(result.mapping_set)
    atomic_write_text(markdown_path, markdown)
    atomic_write_text(html_path, render_html(markdown))
    return markdown_path, html_path


def _bound_graphs(
    key: str,
    config: MappingSetConfig,
    ontology_sources: OntologySourcesConfig,
    cache_dir: Path,
) -> tuple[Graph, Graph]:
    if config.ontologies is None:
        raise ConfigurationError(
            f"Mapping set {key!r} has no ontology binding, so its references cannot be checked. "
            "Add an 'ontologies' entry naming the subject and object ontology sources."
        )
    subject_graph = load_cached_ontology(ontology_sources.get(config.ontologies.subject), cache_dir=cache_dir)
    object_graph = load_cached_ontology(ontology_sources.get(config.ontologies.object), cache_dir=cache_dir)
    return subject_graph, object_graph


def _below(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _refuse_invalid(key: str, report: ValidationReport) -> None:
    if report.is_valid:
        return
    errors = "\n".join(
        f"{issue.location}: {issue.message}" for issue in report.issues if issue.severity is IssueSeverity.ERROR
    )
    raise ValidationError(f"Mapping set {key!r} has referential errors; no artifact was written:\n{errors}")
