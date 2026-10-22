"""Vocabulary source configuration.

The models in this module define the schema of `vocabulary-sources.yaml`.
"""

import re
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ConfigurationError
from plugin_rosetta.utils.io.yaml import load_yaml_mapping
from plugin_rosetta.utils.source_names import validate_portable_source_name

_FILESYSTEM_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validate_filesystem_segment(value: str) -> str:
    if not _FILESYSTEM_SAFE.fullmatch(value):
        raise ValueError(f"must be filesystem safe: {value!r}")
    return value


class ReleaseTable(BaseModel):
    r"""How to locate and validate one required table in a release.

    This is one item of the `tables` list of a vocabulary source. Exactly one
    file in the extracted release must match all non-empty locator fields.
    Unknown fields are rejected.

    Attributes:
        role: Semantic table name that build adapters ask for, for example
            `concept` or `dt-term`. Lowercase letters, digits, and `-`,
            starting with a letter, unique within a source.
        name: Exact file name to match, for example `CONCEPT.csv`.
        prefix: Required start of the file name.
        suffix: Required end of the file name.
        contains: Text that must occur in the release-relative path, which has
            a leading `/`. `/Snapshot/` matches any directory named `Snapshot`.
        separator: Column separator, `","` or a tab (`"\t"` in YAML).
        quote_char: Quote character of the CSV dialect. When omitted, quotes
            have no special meaning.
        contract: Path to the YAML table contract, relative to the registry
            root. It lists `columns:` with a `dtype` (`String`, `Int64`,
            `Float64`, or `Boolean`) and an optional `nullable` flag
            (default true). The file must exist when the configuration loads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    name: str = ""
    prefix: str = ""
    suffix: str = ""
    contains: str = ""
    separator: Literal[",", "\t"]
    quote_char: str | None = None
    contract: Path

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        """Require a lowercase role of letters, digits, and `-`, starting with a letter.

        Raises:
            ValueError: If the role does not match.
        """
        if not re.fullmatch(r"[a-z][a-z0-9-]*", value):
            raise ValueError("must be a lowercase semantic table role")
        return value


class VocabularySourceEntry(BaseModel):
    """Configured fields for one licence-gated vocabulary source.

    This is the value of one entry below `vocabulary_sources:`. Unknown fields
    are rejected.

    Attributes:
        version: Release version, for example `"20260101"`. It is a cache
            directory name: letters, digits, `.`, `_`, and `-`, starting with a
            letter or digit. Quote numeric versions in YAML. `unversioned` is
            accepted but ingesting it produces a warning.
        kind: Release format family: `athena`, `dhd-csv`, or `rf2`.
        description: Free-text description of the source.
        download_page: Absolute `http` or `https` URL of the download page.
        checksum: Expected SHA-256 of the release ZIP as 64 lowercase
            hexadecimal characters. If unset, ingest reports the computed value.
        format_version: Release format marker that must occur in an archive
            member path, compared case-insensitively, for example
            `uitleverformaat4.3`. Only `uitleverformaat<number>` is recognised.
            DHD builds need it to locate the release directory.
        language_refset_id: SNOMED CT language reference set used to select
            preferred terms, for example `"900000000000509007"`. Required for
            `rf2` builds. Quote it in YAML.
        tables: Locators and contracts for the tables that ingest validates and
            build adapters read. Each `role` may occur once.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    kind: Literal["athena", "dhd-csv", "rf2"]
    description: str
    download_page: str
    checksum: str | None = None
    format_version: str | None = None
    language_refset_id: str | None = None
    tables: tuple[ReleaseTable, ...] = ()

    @model_validator(mode="after")
    def validate_unique_table_roles(self) -> Self:
        """Require one table locator per role.

        Raises:
            ValueError: If two tables share a `role`.
        """
        roles = [table.role for table in self.tables]
        duplicates = sorted({role for role in roles if roles.count(role) > 1})
        if duplicates:
            raise ValueError(f"duplicate table roles: {', '.join(duplicates)}")
        return self

    @field_validator("version")
    @classmethod
    def validate_filesystem_safe_version(cls, value: str) -> str:
        """Require a version usable as a cache-path segment.

        Raises:
            ValueError: If the version has characters other than letters,
                digits, `.`, `_`, and `-`, or does not start with a letter or digit.
        """
        return _validate_filesystem_segment(value)

    @field_validator("download_page")
    @classmethod
    def validate_download_page(cls, value: str) -> str:
        """Require an absolute download page URL.

        Raises:
            ValueError: If the URL does not use `http` or `https` or has no host.
        """
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an absolute HTTP(S) URL")
        return value

    @field_validator("checksum")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        """Require a pinned checksum to be 64 lowercase hexadecimal characters.

        Raises:
            ValueError: If the checksum has another form.
        """
        if value is not None and not _SHA256.fullmatch(value):
            raise ValueError("must be a 64-character lowercase SHA-256 digest")
        return value


class VocabularySource(VocabularySourceEntry):
    """A named, pinned vocabulary release ingested from a local ZIP.

    Create instances with `VocabularySourcesConfig.get`.

    Attributes:
        name: Key of the entry below `vocabulary_sources:`, for example `omop`.
            Build functions look up `omop`, `dhd-thesauri`, `loinc-snomed`, and
            `snomed-international`. It must be a portable path segment:
            lowercase letters, digits, `.`, `_`, and `-`, starting with a
            letter or digit, and not a reserved Windows device name.
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


class VocabularySourcesConfig(BaseModel):
    """Validated vocabulary source registry.

    This is the root of `vocabulary-sources.yaml`.

    Attributes:
        vocabulary_sources: Entries by name; see `VocabularySource.name`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    vocabulary_sources: dict[str, VocabularySourceEntry]

    @model_validator(mode="after")
    def validate_source_names(self) -> Self:
        """Require every key to be a portable lowercase path segment.

        Raises:
            ValueError: If a key is not a portable lowercase path segment.
        """
        for name in self.vocabulary_sources:
            validate_portable_source_name(name)
        return self

    def get(self, name: str) -> VocabularySource:
        """Return a configured vocabulary source by name.

        Raises:
            ConfigurationError: If `name` is not configured. The message lists
                the known names.
        """
        try:
            entry = self.vocabulary_sources[name]
        except KeyError as error:
            known = ", ".join(sorted(self.vocabulary_sources))
            raise ConfigurationError(
                f"Unknown vocabulary source {name!r}. Known vocabulary sources: {known}"
            ) from error
        return VocabularySource(name=name, **entry.model_dump())


def load_vocabulary_sources(path: Path, *, registry_root: Path | None = None) -> VocabularySourcesConfig:
    """Load and validate the vocabulary source registry.

    Table contract files must exist; their content is not checked here.

    Args:
        path: Path to `vocabulary-sources.yaml`.
        registry_root: Directory that `contract` paths are relative to.
            Defaults to the parent of the directory containing `path`.

    Raises:
        ConfigurationError: If the file cannot be read, is not valid YAML, has
            a duplicate key, fails validation, or references a missing
            contract file.
    """
    raw_config = load_yaml_mapping(path)
    try:
        config = VocabularySourcesConfig.model_validate(raw_config)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid vocabulary source configuration in {path}: {error}") from error

    root = registry_root or path.parent.parent
    for name, source in config.vocabulary_sources.items():
        for table in source.tables:
            contract_path = root / table.contract
            if not contract_path.is_file():
                raise ConfigurationError(
                    f"Vocabulary source {name!r} references missing contract for role {table.role!r}: {contract_path}"
                )
    return config
