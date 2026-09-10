"""Provenance sidecars for generated vocabulary graphs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from plugin_rosetta.utils.io.atomic import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path


class VocabularyProvenance(BaseModel):
    """Source release identity and build time for one graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_name: str
    source_version: str
    format_version: str | None
    as_of: str | None = None
    built_at: str


def write_provenance(
    turtle_path: Path,
    *,
    source_name: str,
    source_version: str,
    format_version: str | None,
    as_of: str | None = None,
) -> Path:
    """Write the provenance sidecar beside a Turtle graph."""
    provenance = VocabularyProvenance(
        source_name=source_name,
        source_version=source_version,
        format_version=format_version,
        as_of=as_of,
        built_at=datetime.now(UTC).isoformat(),
    )
    destination = turtle_path.with_suffix(".meta.json")
    atomic_write_text(destination, json.dumps(provenance.model_dump(), indent=2) + "\n")
    return destination
