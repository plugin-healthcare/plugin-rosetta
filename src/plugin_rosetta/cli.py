"""Command-line interface for plugin-rosetta."""

from pathlib import Path
from typing import Annotated

import typer

from plugin_rosetta.application.mapping import (
    DEFAULT_MAPPING_CONFIG,
    build_mapping_artifacts,
    read_mapping_set,
    report_mapping_set,
)
from plugin_rosetta.application.mapping_sets import list_mapping_sets

app = typer.Typer(
    help="Rosetta mapping toolbox.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
mapping_app = typer.Typer(help="Work with authored mapping sets.", rich_markup_mode=None)
app.add_typer(mapping_app, name="mapping")


@app.callback()
def main() -> None:
    """Author and publish open mapping artifacts."""


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
    for key, mapping_file in list_mapping_sets(config, root=root):
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
) -> None:
    """Check graph-free mapping schema conformance."""
    result = read_mapping_set(key, config_path=config, root=root)
    typer.echo(f"{len(result.mapping_set.mappings or [])} conforming rows")
    if result.report.issues:
        typer.echo(f"{len(result.report.issues)} input warnings")


@mapping_app.command("build")
def build_mapping_set_command(
    key: Annotated[str, typer.Argument(help="Configured mapping-set key.")],
    output_dir: Annotated[Path, typer.Option(help="Directory for generated artifacts.")],
    config: Annotated[Path, typer.Option(help="Path to the mapping-set configuration.")] = DEFAULT_MAPPING_CONFIG,
    root: Annotated[Path, typer.Option(help="Root used to resolve configured paths.")] = Path(),
) -> None:
    """Build SSSOM and Turtle artifacts."""
    for path in build_mapping_artifacts(key, output_dir=output_dir, config_path=config, root=root):
        typer.echo(path)


@mapping_app.command("report")
def report_mapping_set_command(
    key: Annotated[str, typer.Argument(help="Configured mapping-set key.")],
    output_dir: Annotated[Path, typer.Option(help="Directory for generated reports.")],
    config: Annotated[Path, typer.Option(help="Path to the mapping-set configuration.")] = DEFAULT_MAPPING_CONFIG,
    root: Annotated[Path, typer.Option(help="Root used to resolve configured paths.")] = Path(),
) -> None:
    """Write Markdown and HTML reports."""
    for path in report_mapping_set(key, output_dir=output_dir, config_path=config, root=root):
        typer.echo(path)
