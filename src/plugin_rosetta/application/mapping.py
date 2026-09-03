"""Graph-free mapping use cases."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from linkml_runtime.utils.metamodelcore import URI

from plugin_rosetta.config.mapping_sets import load_mapping_sets
from plugin_rosetta.io._atomic import atomic_write_text
from plugin_rosetta.io.csvw import read_mapping_rows
from plugin_rosetta.io.rdf import write_turtle
from plugin_rosetta.io.sssom import write_sssom_tsv
from plugin_rosetta.mapping.models.sssom import MappingSet
from plugin_rosetta.mapping.report import render_html, render_markdown
from plugin_rosetta.mapping.validate import validate_schema_conformance

if TYPE_CHECKING:
    from plugin_rosetta.core.report import ValidationReport

DEFAULT_MAPPING_CONFIG = Path("registry/config/mapping-sets.yaml")


@dataclass(frozen=True)
class MappingReadResult:
    """Validated mapping set and non-fatal source issues."""

    mapping_set: MappingSet
    report: ValidationReport


def read_mapping_set(
    key: str,
    *,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
) -> MappingReadResult:
    """Read a configured mapping set without loading an ontology graph."""
    resolved_root = (root or Path.cwd()).resolve()
    config = load_mapping_sets(config_path, root=resolved_root).get(key)
    rows = read_mapping_rows(
        config.mapping_file_path(resolved_root),
        config.metadata_file_path(resolved_root),
    )
    mappings = validate_schema_conformance(rows.rows)
    mapping_set = MappingSet(
        mapping_set_id=URI(config.mapping_set_id),
        license=URI(config.license),
        curie_map=config.curie_map,
        mappings=list(mappings),
    )
    return MappingReadResult(mapping_set=mapping_set, report=rows.report)


def build_mapping_artifacts(
    key: str,
    *,
    output_dir: Path,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
) -> tuple[Path, Path]:
    """Build portable SSSOM and Turtle artifacts."""
    result = read_mapping_set(key, config_path=config_path, root=root)
    sssom_path = output_dir / f"{key}.sssom.tsv"
    turtle_path = output_dir / f"{key}.ttl"
    write_sssom_tsv(result.mapping_set, sssom_path)
    write_turtle(result.mapping_set, turtle_path)
    return sssom_path, turtle_path


def report_mapping_set(
    key: str,
    *,
    output_dir: Path,
    config_path: Path = DEFAULT_MAPPING_CONFIG,
    root: Path | None = None,
) -> tuple[Path, Path]:
    """Write portable Markdown and HTML reports."""
    result = read_mapping_set(key, config_path=config_path, root=root)
    markdown_path = output_dir / f"{key}.md"
    html_path = output_dir / f"{key}.html"
    markdown = render_markdown(result.mapping_set)
    atomic_write_text(markdown_path, markdown)
    atomic_write_text(html_path, render_html(markdown))
    return markdown_path, html_path
