"""CURIE expansion."""

from typing import TYPE_CHECKING

from curies import Converter

from plugin_rosetta.core.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping


def expand_curie(value: str, curie_map: Mapping[str, str]) -> str:
    """Expand a CURIE with an explicit prefix map."""
    if ":" not in value:
        raise ValidationError(f"Value is not a CURIE: {value!r}")
    expanded = Converter.from_prefix_map(dict(curie_map)).expand(value)
    if expanded is None:
        known = ", ".join(sorted(curie_map))
        prefix = value.partition(":")[0]
        raise ValidationError(f"CURIE prefix {prefix!r} is unknown. Known prefixes: {known}")
    return expanded
