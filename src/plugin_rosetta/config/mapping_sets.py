"""Mapping-set configuration."""

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.core.errors import ConfigurationError
from plugin_rosetta.io.yaml import load_yaml_mapping

if TYPE_CHECKING:
    from plugin_rosetta.config.ontology_sources import OntologySourcesConfig


class MappingSetOntologies(BaseModel):
    """Ontology sources that must resolve a mapping set's subjects and objects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    object: str


class MappingSetConfig(BaseModel):
    """Configuration for one authored mapping set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mapping_set_id: str
    license: str
    mapping_file: Path
    metadata_file: Path
    curie_map: dict[str, str] = Field(min_length=1)
    ontologies: MappingSetOntologies | None = None

    @field_validator("mapping_set_id", "license")
    @classmethod
    def validate_absolute_iri(cls, value: str) -> str:
        """Require an absolute identifier."""
        if not urlsplit(value).scheme:
            raise ValueError("must be an absolute IRI")
        return value

    @field_validator("curie_map")
    @classmethod
    def validate_curie_map(cls, value: dict[str, str]) -> dict[str, str]:
        """Require usable namespace prefixes."""
        for prefix, namespace in value.items():
            if not prefix or not urlsplit(namespace).scheme or not namespace.endswith(("/", "#")):
                raise ValueError(f"invalid namespace for prefix {prefix!r}: {namespace!r}")
        return value

    def mapping_file_path(self, root: Path) -> Path:
        """Return the mapping CSV path below the configured root."""
        return root / self.mapping_file

    def metadata_file_path(self, root: Path) -> Path:
        """Return the CSVW metadata path below the configured root."""
        return root / self.metadata_file


class MappingSetsConfig(BaseModel):
    """Validated mapping-set catalogue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mapping_sets: dict[str, MappingSetConfig]

    def get(self, key: str) -> MappingSetConfig:
        """Return a configured mapping set."""
        try:
            return self.mapping_sets[key]
        except KeyError as error:
            known = ", ".join(sorted(self.mapping_sets))
            raise ConfigurationError(f"Unknown mapping set {key!r}. Known mapping sets: {known}") from error


def load_mapping_sets(
    path: Path,
    *,
    root: Path | None = None,
    ontology_sources: OntologySourcesConfig | None = None,
) -> MappingSetsConfig:
    """Load mapping-set configuration and verify referenced files.

    When `ontology_sources` is supplied, every ontology binding is resolved
    here so an unconfigured source fails at load time rather than halfway
    through validation.
    """
    resolved_root = (root or Path.cwd()).resolve()
    config_path = path if path.is_absolute() else resolved_root / path
    raw_config = load_yaml_mapping(config_path)
    try:
        config = MappingSetsConfig.model_validate(raw_config)
    except PydanticValidationError as error:
        raise ConfigurationError(f"Invalid mapping-set configuration in {config_path}: {error}") from error

    for key, mapping_set in config.mapping_sets.items():
        for referenced_path in (
            mapping_set.mapping_file_path(resolved_root),
            mapping_set.metadata_file_path(resolved_root),
        ):
            if not referenced_path.is_file():
                raise ConfigurationError(f"Mapping set {key!r} references missing file: {referenced_path}")
        if ontology_sources is not None and mapping_set.ontologies is not None:
            _resolve_bindings(key, mapping_set.ontologies, ontology_sources)
    return config


def _resolve_bindings(key: str, bindings: MappingSetOntologies, ontology_sources: OntologySourcesConfig) -> None:
    for name in (bindings.subject, bindings.object):
        try:
            ontology_sources.get(name)
        except ConfigurationError as error:
            raise ConfigurationError(f"Mapping set {key!r} binds an unconfigured ontology source: {error}") from error
