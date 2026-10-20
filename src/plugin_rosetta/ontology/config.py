"""Ontology source configuration.

The models in this module define the schema of `ontology-sources.yaml`.
"""

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ConfigurationError, RosettaIOError
from plugin_rosetta.utils.io.yaml import load_yaml_mapping
from plugin_rosetta.utils.source_names import validate_portable_source_name

if TYPE_CHECKING:
    from pathlib import Path

_FILESYSTEM_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class OntologySourceEntry(BaseModel):
    """Configured fields for one pinned ontology source, as authored in YAML.

    This is the value of one entry below `ontology_sources:`. Unknown fields
    are rejected.

    Attributes:
        version: Release version, for example `"2.8.1"`. It is a cache directory
            name: letters, digits, `.`, `_`, and `-`, starting with a letter or
            digit. Quote numeric versions in YAML.
        iri: Absolute IRI of the ontology.
        download_url: URL of the Turtle file for this version.
        checksum: Expected SHA-256 of the file as 64 lowercase hexadecimal
            characters. If unset, a fetch reports the computed value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    iri: str
    download_url: str
    checksum: str | None = None

    @field_validator("version")
    @classmethod
    def validate_filesystem_safe_version(cls, value: str) -> str:
        """Require a version usable as a cache-path segment.

        Raises:
            ValueError: If the version has characters other than letters,
                digits, `.`, `_`, and `-`, or does not start with a letter or digit.
        """
        if not _FILESYSTEM_SAFE.fullmatch(value):
            raise ValueError(f"must be filesystem safe: {value!r}")
        return value

    @field_validator("iri")
    @classmethod
    def validate_absolute_iri(cls, value: str) -> str:
        """Require an absolute IRI.

        Raises:
            ValueError: If the IRI has no URI scheme such as `http:`.
        """
        if not urlsplit(value).scheme:
            raise ValueError("must be an absolute IRI")
        return value


class OntologySource(OntologySourceEntry):
    """A pinned ontology source: a configured entry combined with its name.

    Create instances with `OntologySourcesConfig.get`.

    Attributes:
        name: Key of the entry below `ontology_sources:`, for example `onz-g`.
            It must be a portable path segment: lowercase letters, digits,
            `.`, `_`, and `-`, starting with a letter or digit, and not a
            reserved Windows device name.
    """

    name: str

    @field_validator("name")
    @classmethod
    def validate_filesystem_safe_name(cls, value: str) -> str:
        """Require a name usable as one cache-path segment.

        Raises:
            ValueError: If the name is not a portable lowercase path segment.
        """
        return validate_portable_source_name(value)

    def cache_path(self, cache_dir: Path) -> Path:
        """Return `<cache_dir>/<name>/<version>/ontology.ttl`; existence is not checked.

        Args:
            cache_dir: Root directory of the ontology cache.

        Raises:
            RosettaIOError: If the path would resolve outside `cache_dir`.
        """
        path = cache_dir / self.name / self.version / "ontology.ttl"
        if not path.resolve().is_relative_to(cache_dir.resolve()):
            raise RosettaIOError(
                f"Ontology cache path for source {self.name!r} resolves outside cache root {cache_dir}"
            )
        return path


class OntologySourcesConfig(BaseModel):
    """Validated ontology source registry.

    This is the root of `ontology-sources.yaml`.

    Attributes:
        ontology_sources: Entries by name; see `OntologySource.name`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ontology_sources: dict[str, OntologySourceEntry]

    @model_validator(mode="after")
    def validate_source_names(self) -> OntologySourcesConfig:
        """Require every key to be a portable lowercase path segment.

        Raises:
            ValueError: If a key is not a portable lowercase path segment.
        """
        for name in self.ontology_sources:
            validate_portable_source_name(name)
        return self

    def get(self, name: str) -> OntologySource:
        """Return a configured ontology source by name.

        Raises:
            ConfigurationError: If `name` is not configured. The message lists
                the known names.
        """
        try:
            entry = self.ontology_sources[name]
        except KeyError as error:
            known = ", ".join(sorted(self.ontology_sources))
            raise ConfigurationError(f"Unknown ontology source {name!r}. Known ontology sources: {known}") from error
        return OntologySource(name=name, **entry.model_dump())


def load_ontology_sources(path: Path) -> OntologySourcesConfig:
    """Load and validate the ontology source registry.

    Args:
        path: Path to `ontology-sources.yaml`.

    Raises:
        ConfigurationError: If the file cannot be read, is not valid YAML,
            has a duplicate key, or fails validation.
    """
    raw_config = load_yaml_mapping(path)
    try:
        return OntologySourcesConfig.model_validate(raw_config)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid ontology source configuration in {path}: {error}") from error
