"""Vocabulary source configuration."""

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.core.errors import ConfigurationError
from plugin_rosetta.core.paths import validate_portable_source_name
from plugin_rosetta.io.yaml import load_yaml_mapping

if TYPE_CHECKING:
    from pathlib import Path

_FILESYSTEM_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validate_filesystem_segment(value: str) -> str:
    if not _FILESYSTEM_SAFE.fullmatch(value):
        raise ValueError(f"must be filesystem safe: {value!r}")
    return value


class ReleaseTable(BaseModel):
    """How to locate and validate one required table in a release."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = ""
    prefix: str = ""
    suffix: str = ""
    contains: str = ""
    separator: Literal[",", "\t"]
    quote_char: str | None = None
    contract: str

    @field_validator("contract")
    @classmethod
    def validate_contract_path(cls, value: str) -> str:
        """Keep contract references relative to the registry root."""
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("must be a relative path within the registry")
        return value


class VocabularySourceEntry(BaseModel):
    """Configured fields for one licence-gated vocabulary source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    kind: Literal["athena", "dhd-csv", "rf2"]
    description: str
    download_page: str
    checksum: str | None = None
    format_version: str | None = None
    tables: tuple[ReleaseTable, ...] = ()

    @field_validator("version")
    @classmethod
    def validate_filesystem_safe_version(cls, value: str) -> str:
        """Require a version usable as a cache-path segment."""
        return _validate_filesystem_segment(value)

    @field_validator("download_page")
    @classmethod
    def validate_download_page(cls, value: str) -> str:
        """Require an absolute download page URL."""
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an absolute HTTP(S) URL")
        return value

    @field_validator("checksum")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        """Require a canonical SHA-256 digest when one is pinned."""
        if value is not None and not _SHA256.fullmatch(value):
            raise ValueError("must be a 64-character lowercase SHA-256 digest")
        return value


class VocabularySource(VocabularySourceEntry):
    """A named, pinned vocabulary release ingested from a local ZIP."""

    name: str

    @field_validator("name")
    @classmethod
    def validate_filesystem_safe_name(cls, value: str) -> str:
        """Require a name usable as one cache-path segment."""
        return validate_portable_source_name(value)


class VocabularySourcesConfig(BaseModel):
    """Validated vocabulary source registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vocabulary_sources: dict[str, VocabularySourceEntry]

    @model_validator(mode="after")
    def validate_source_names(self) -> VocabularySourcesConfig:
        """Reject registry keys that could escape the cache root."""
        for name in self.vocabulary_sources:
            validate_portable_source_name(name)
        return self

    def get(self, name: str) -> VocabularySource:
        """Return a configured vocabulary source by name."""
        try:
            entry = self.vocabulary_sources[name]
        except KeyError as error:
            known = ", ".join(sorted(self.vocabulary_sources))
            raise ConfigurationError(
                f"Unknown vocabulary source {name!r}. Known vocabulary sources: {known}"
            ) from error
        return VocabularySource(name=name, **entry.model_dump())


def load_vocabulary_sources(path: Path) -> VocabularySourcesConfig:
    """Load and validate the vocabulary source registry."""
    raw_config = load_yaml_mapping(path)
    try:
        return VocabularySourcesConfig.model_validate(raw_config)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid vocabulary source configuration in {path}: {error}") from error
