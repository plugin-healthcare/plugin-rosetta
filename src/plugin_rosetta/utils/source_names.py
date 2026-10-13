"""Portable source-name validation shared by source catalogues."""

import re

_PORTABLE_SEGMENT = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9_-])?$")
_WINDOWS_RESERVED = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def validate_portable_source_name(value: str) -> str:
    """Require one lowercase path segment that is portable across supported systems."""
    if not _PORTABLE_SEGMENT.fullmatch(value) or value.casefold() in _WINDOWS_RESERVED:
        raise ValueError(f"must be a portable lowercase filesystem name: {value!r}")
    return value
