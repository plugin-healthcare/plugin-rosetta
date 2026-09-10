"""Command-line interface for plugin-rosetta."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from plugin_rosetta.errors import RosettaError
from plugin_rosetta.mapping import (
    DEFAULT_MAPPING_CONFIG,
    build_mapping_artifacts,
    list_mapping_sets,
    read_mapping_set,
    report_mapping_set,
)
from plugin_rosetta.ontology import (
    DEFAULT_ONTOLOGY_CONFIG,
    fetch_ontology_source,
)
from plugin_rosetta.ontology.loader import DEFAULT_CACHE_DIR as DEFAULT_ONTOLOGY_CACHE_DIR
from plugin_rosetta.vocabulary import (
    DEFAULT_VOCABULARY_CONFIG,
    DEFAULT_VOCABULARY_OUTPUT_DIR,
    build_cached_dhd_graph,
    build_cached_omop_graph,
    ingest_release,
)
from plugin_rosetta.vocabulary.ingest import DEFAULT_CACHE_DIR as DEFAULT_VOCABULARY_CACHE_DIR
from plugin_rosetta.workspace import initialize_workspace

if TYPE_CHECKING:
    from collections.abc import Callable

app = typer.Typer(
    help="Rosetta mapping toolbox.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
mapping_app = typer.Typer(help="Work with authored mapping sets.", rich_markup_mode=None)
app.add_typer(mapping_app, name="mapping")
ontology_app = typer.Typer(help="Fetch and cache ontology sources.", rich_markup_mode=None)
app.add_typer(ontology_app, name="ontology")
vocabulary_app = typer.Typer(help="Ingest and validate vocabulary releases.", rich_markup_mode=None)
app.add_typer(vocabulary_app, name="vocabulary")


def _guard[T](operation: Callable[[], T]) -> T:
    """Report an expected Rosetta failure as a CLI error instead of a traceback."""
    try:
        return operation()
    except RosettaError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=1) from error


@app.callback()
def main() -> None:
    """Author and publish open mapping artifacts."""


@app.command("init")
def initialize_workspace_command(
    destination: Annotated[
        Path,
        typer.Argument(help="Directory in which to create rosetta.yaml and registry/."),
    ] = Path(),
) -> None:
    """Initialize an empty workspace for user-supplied registry inputs."""
    config_path = _guard(lambda: initialize_workspace(destination))
    typer.echo(config_path)


@mapping_app.command("list")
def list_mapping_sets_command(
    config: Annotated[
        Path,
        typer.Option(help="Path to the mapping-set configuration."),
    ] = Path("registry/config/mapping-sets.yaml"),
    root: Annotated[
        Path,
        typer.Option(help="Root used to resolve paths in the configuration."),
    ] = Path(),
) -> None:
    """List configured mapping sets."""
    for key, mapping_file in _guard(lambda: list(list_mapping_sets(config, root=root))):
        typer.echo(f"{key}\t{mapping_file}")


@mapping_app.command("validate")
def validate_mapping_set_command(
    key: Annotated[str, typer.Argument(help="Configured mapping-set key.")],
    config: Annotated[
        Path,
        typer.Option(help="Path to the mapping-set configuration."),
    ] = DEFAULT_MAPPING_CONFIG,
    root: Annotated[
        Path,
        typer.Option(help="Root used to resolve configured paths."),
    ] = Path(),
    check_references: Annotated[
        bool,
        typer.Option(help="Also resolve every subject and object against its bound ontology."),
    ] = False,
    ontology_config: Annotated[
        Path,
        typer.Option(help="Path to the ontology source configuration."),
    ] = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Annotated[
        Path,
        typer.Option(help="Base directory holding cached ontologies."),
    ] = DEFAULT_ONTOLOGY_CACHE_DIR,
) -> None:
    """Check mapping schema conformance and, optionally, referential integrity."""
    result = _guard(
        lambda: read_mapping_set(
            key,
            config_path=config,
            root=root,
            check_references=check_references,
            ontology_config_path=ontology_config,
            cache_dir=cache_dir,
        )
    )
    typer.echo(f"{len(result.mapping_set.mappings or [])} conforming rows")
    for issue in result.report.issues:
        typer.echo(f"{issue.severity}: {issue.location}: {issue.message}")
    if not result.report.is_valid:
        raise typer.Exit(code=1)


@mapping_app.command("build")
def build_mapping_set_command(
    key: Annotated[str, typer.Argument(help="Configured mapping-set key.")],
    output_dir: Annotated[Path, typer.Option(help="Directory for generated artifacts.")],
    config: Annotated[Path, typer.Option(help="Path to the mapping-set configuration.")] = DEFAULT_MAPPING_CONFIG,
    root: Annotated[Path, typer.Option(help="Root used to resolve configured paths.")] = Path(),
    check_references: Annotated[
        bool,
        typer.Option(help="Refuse to write unless every subject and object resolves."),
    ] = False,
    ontology_config: Annotated[
        Path,
        typer.Option(help="Path to the ontology source configuration."),
    ] = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Annotated[
        Path,
        typer.Option(help="Base directory holding cached ontologies."),
    ] = DEFAULT_ONTOLOGY_CACHE_DIR,
) -> None:
    """Build SSSOM and Turtle artifacts."""
    artifacts = _guard(
        lambda: build_mapping_artifacts(
            key,
            output_dir=output_dir,
            config_path=config,
            root=root,
            check_references=check_references,
            ontology_config_path=ontology_config,
            cache_dir=cache_dir,
        )
    )
    for path in artifacts:
        typer.echo(path)


@mapping_app.command("report")
def report_mapping_set_command(
    key: Annotated[str, typer.Argument(help="Configured mapping-set key.")],
    output_dir: Annotated[Path, typer.Option(help="Directory for generated reports.")],
    config: Annotated[Path, typer.Option(help="Path to the mapping-set configuration.")] = DEFAULT_MAPPING_CONFIG,
    root: Annotated[Path, typer.Option(help="Root used to resolve configured paths.")] = Path(),
) -> None:
    """Write Markdown and HTML reports."""
    reports = _guard(lambda: report_mapping_set(key, output_dir=output_dir, config_path=config, root=root))
    for path in reports:
        typer.echo(path)


@ontology_app.command("fetch")
def fetch_ontology_source_command(
    name: Annotated[str, typer.Argument(help="Configured ontology source name.")],
    config: Annotated[
        Path,
        typer.Option(help="Path to the ontology source configuration."),
    ] = DEFAULT_ONTOLOGY_CONFIG,
    cache_dir: Annotated[
        Path,
        typer.Option(help="Base directory used to cache downloaded ontologies."),
    ] = DEFAULT_ONTOLOGY_CACHE_DIR,
    force: Annotated[
        bool,
        typer.Option(help="Re-download even if the ontology is already cached."),
    ] = False,
) -> None:
    """Download and cache a configured ontology source."""
    path, report = _guard(lambda: fetch_ontology_source(name, config_path=config, cache_dir=cache_dir, force=force))
    typer.echo(path)
    for issue in report.issues:
        typer.echo(f"{issue.severity}: {issue.message}")


@vocabulary_app.command("ingest")
def ingest_vocabulary_release_command(
    name: Annotated[str, typer.Argument(help="Configured vocabulary source name.")],
    zip_path: Annotated[Path, typer.Argument(help="Path to the manually downloaded release ZIP.")],
    config: Annotated[
        Path,
        typer.Option(help="Path to the vocabulary source configuration."),
    ] = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Annotated[
        Path,
        typer.Option(help="Base directory used to cache vocabulary releases."),
    ] = DEFAULT_VOCABULARY_CACHE_DIR,
    force: Annotated[
        bool,
        typer.Option(help="Re-extract even if the release is already cached."),
    ] = False,
) -> None:
    """Verify and cache a licence-gated vocabulary release."""
    path, report = _guard(lambda: ingest_release(name, zip_path, config_path=config, cache_dir=cache_dir, force=force))
    typer.echo(path)
    for issue in report.issues:
        typer.echo(f"{issue.severity}: {issue.message}")


@vocabulary_app.command("build-omop")
def build_omop_vocabulary_command(
    output_dir: Annotated[
        Path,
        typer.Option(help="Directory in which to write the OMOP graph."),
    ] = DEFAULT_VOCABULARY_OUTPUT_DIR,
    config: Annotated[
        Path,
        typer.Option(help="Path to the vocabulary source configuration."),
    ] = DEFAULT_VOCABULARY_CONFIG,
    cache_dir: Annotated[
        Path,
        typer.Option(help="Base directory holding ingested vocabulary releases."),
    ] = DEFAULT_VOCABULARY_CACHE_DIR,
) -> None:
    """Build an OMOP graph from the configured ingested release."""
    artifacts = _guard(
        lambda: build_cached_omop_graph(
            output_dir,
            config_path=config,
            cache_dir=cache_dir,
        )
    )
    for path in artifacts:
        typer.echo(path)


def _build_dhd_command(
    thesaurus: str,
    as_of: str,
    output_dir: Path,
    config: Path,
    cache_dir: Path,
) -> None:
    artifacts = _guard(
        lambda: build_cached_dhd_graph(
            thesaurus,
            as_of=as_of,
            output_dir=output_dir,
            config_path=config,
            cache_dir=cache_dir,
        )
    )
    for path in artifacts:
        typer.echo(path)


@vocabulary_app.command("build-dhd-diagnosethesaurus")
def build_dhd_diagnosethesaurus_command(
    as_of: Annotated[str, typer.Option(help="Validity date in YYYYMMDD format.")],
    output_dir: Annotated[Path, typer.Option(help="Directory in which to write the DHD graph.")] = (
        DEFAULT_VOCABULARY_OUTPUT_DIR
    ),
    config: Annotated[Path, typer.Option(help="Path to the vocabulary source configuration.")] = (
        DEFAULT_VOCABULARY_CONFIG
    ),
    cache_dir: Annotated[Path, typer.Option(help="Base directory holding ingested releases.")] = (
        DEFAULT_VOCABULARY_CACHE_DIR
    ),
) -> None:
    """Build the DHD Diagnosethesaurus graph."""
    _build_dhd_command("dt", as_of, output_dir, config, cache_dir)


@vocabulary_app.command("build-dhd-verrichtingenthesaurus")
def build_dhd_verrichtingenthesaurus_command(
    as_of: Annotated[str, typer.Option(help="Validity date in YYYYMMDD format.")],
    output_dir: Annotated[Path, typer.Option(help="Directory in which to write the DHD graph.")] = (
        DEFAULT_VOCABULARY_OUTPUT_DIR
    ),
    config: Annotated[Path, typer.Option(help="Path to the vocabulary source configuration.")] = (
        DEFAULT_VOCABULARY_CONFIG
    ),
    cache_dir: Annotated[Path, typer.Option(help="Base directory holding ingested releases.")] = (
        DEFAULT_VOCABULARY_CACHE_DIR
    ),
) -> None:
    """Build the DHD Verrichtingenthesaurus graph."""
    _build_dhd_command("vt", as_of, output_dir, config, cache_dir)
