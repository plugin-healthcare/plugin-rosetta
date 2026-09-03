"""Mapping-set catalogue use cases."""

from typing import TYPE_CHECKING

from plugin_rosetta.config.mapping_sets import load_mapping_sets

if TYPE_CHECKING:
    from pathlib import Path


def list_mapping_sets(config_path: Path, *, root: Path) -> tuple[tuple[str, Path], ...]:
    """List configured mapping-set keys and source files."""
    config = load_mapping_sets(config_path, root=root)
    return tuple((key, value.mapping_file) for key, value in config.mapping_sets.items())
