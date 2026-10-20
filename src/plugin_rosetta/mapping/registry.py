"""Mapping-set catalogue use cases."""

from typing import TYPE_CHECKING

from plugin_rosetta.mapping.config import load_mapping_sets

if TYPE_CHECKING:
    from pathlib import Path


def list_mapping_sets(config_path: Path, *, root: Path) -> tuple[tuple[str, Path], ...]:
    """List configured mapping-set keys and source files.

    The configuration is loaded and validated first, so a missing mapping or
    metadata file raises.

    Args:
        config_path: Path to `mapping-sets.yaml`, relative to `root` unless absolute.
        root: Workspace root for relative paths.

    Returns:
        One `(key, mapping_file)` pair per mapping set, in configuration order.
        `mapping_file` is the path as written in the configuration.

    Raises:
        ConfigurationError: If the configuration is invalid or references a
            missing file.
    """
    config = load_mapping_sets(config_path, root=root)
    return tuple((key, value.mapping_file) for key, value in config.mapping_sets.items())
