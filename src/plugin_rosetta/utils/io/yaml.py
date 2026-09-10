"""Strict YAML input utilities."""

from collections.abc import Hashable
from typing import TYPE_CHECKING, Any

import yaml
import yaml.resolver

from plugin_rosetta.errors import ConfigurationError

if TYPE_CHECKING:
    from pathlib import Path


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Hashable, Any]:
    result: dict[Hashable, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            raise ConfigurationError(f"YAML mapping key is not hashable at line {key_node.start_mark.line + 1}")
        if key in result:
            raise ConfigurationError(f"duplicate key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML document whose root is a mapping."""
    try:
        content = path.read_text()
    except OSError as error:
        raise ConfigurationError(f"Cannot read YAML configuration {path}: {error}") from error
    try:
        # _UniqueKeyLoader subclasses yaml.SafeLoader and only overrides mapping
        # construction, so this call carries no unsafe deserialization risk.
        result = yaml.load(content, Loader=_UniqueKeyLoader)  # noqa: S506
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML configuration {path}: {error}") from error
    if not isinstance(result, dict):
        raise ConfigurationError(f"YAML configuration root must be a mapping: {path}")
    return result
