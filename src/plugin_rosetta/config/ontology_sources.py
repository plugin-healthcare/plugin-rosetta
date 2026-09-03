"""Ontology source configuration."""

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.core.errors import ConfigurationError
from plugin_rosetta.io.yaml import load_yaml_mapping

if TYPE_CHECKING:
    from pathlib import Path

_FILESYSTEM_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class OntologySourceEntry(BaseModel):
    """Configured fields for one pinned ontology source, as authored in YAML."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    iri: str
    download_url: str
    checksum: str | None = None

    @field_validator("version")
    @classmethod
    def validate_filesystem_safe_version(cls, value: str) -> str:
        """Require a version usable as a cache-path segment."""
        if not _FILESYSTEM_SAFE.fullmatch(value):
            raise ValueError(f"must be filesystem safe: {value!r}")
        return value

    @field_validator("iri")
    @classmethod
    def validate_absolute_iri(cls, value: str) -> str:
        """Require an absolute identifier."""
        if not urlsplit(value).scheme:
            raise ValueError("must be an absolute IRI")
        return value


class OntologySource(BaseModel):
    """A pinned ontology source: identity, version, and where to fetch it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    iri: str
    download_url: str
    checksum: str | None = None

    def cache_path(self, cache_dir: Path) -> Path:
        """Return the local cache path for this source's ontology file."""
        return cache_dir / self.name / self.version / "ontology.ttl"


class OntologySourcesConfig(BaseModel):
    """Validated ontology source registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ontology_sources: dict[str, OntologySourceEntry]

    def get(self, name: str) -> OntologySource:
        """Return a configured ontology source by name."""
        try:
            entry = self.ontology_sources[name]
        except KeyError as error:
            known = ", ".join(sorted(self.ontology_sources))
            raise ConfigurationError(f"Unknown ontology source {name!r}. Known ontology sources: {known}") from error
        return OntologySource(name=name, **entry.model_dump())


def load_ontology_sources(path: Path) -> OntologySourcesConfig:
    """Load and validate the ontology source registry."""
    raw_config = load_yaml_mapping(path)
    try:
        return OntologySourcesConfig.model_validate(raw_config)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid ontology source configuration in {path}: {error}") from error
