"""Mapping-set configuration.

The models in this module define the schema of `mapping-sets.yaml`.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from plugin_rosetta.errors import ConfigurationError
from plugin_rosetta.utils.io.yaml import load_yaml_mapping
from plugin_rosetta.utils.source_names import validate_portable_source_name

if TYPE_CHECKING:
    from plugin_rosetta.ontology.config import OntologySourcesConfig


class MappingSetOntologies(BaseModel):
    """Ontology sources that must resolve a mapping set's subjects and objects.

    This is the `ontologies` block of a mapping-set entry. It is used when
    references are checked.

    Attributes:
        subject: Ontology source name, from `ontology-sources.yaml`, that must
            contain every `subject_id`, for example `omop-cdm`.
        object: Ontology source name that must contain every `object_id`,
            for example `onz-g`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    object: str


class MappingSetConfig(BaseModel):
    """Configuration for one authored mapping set.

    This is the value of one entry below `mapping_sets:`. Unknown fields are
    rejected.

    Attributes:
        mapping_set_id: Absolute IRI of the published mapping set; becomes the
            SSSOM `mapping_set_id`.
        license: Absolute IRI of the licence.
        mapping_file: Path to the mapping CSV, relative to the workspace root.
        metadata_file: Path to the CSVW metadata JSON of `mapping_file`,
            relative to the workspace root.
        curie_map: Prefixes used to expand CURIEs. It needs at least one entry,
            and each namespace must be an absolute IRI ending in `/` or `#`.
            Include prefixes for predicates and other CURIE-valued columns.
        ontologies: Optional binding to the ontology sources used for checking
            references. Without it, references cannot be checked.
    """

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
        """Require an absolute IRI.

        Raises:
            ValueError: If the value has no URI scheme such as `https:`.
        """
        if not urlsplit(value).scheme:
            raise ValueError("must be an absolute IRI")
        return value

    @field_validator("curie_map")
    @classmethod
    def validate_curie_map(cls, value: dict[str, str]) -> dict[str, str]:
        """Require non-empty prefixes and absolute namespaces ending in `/` or `#`.

        Raises:
            ValueError: If a prefix is empty or a namespace is invalid.
        """
        for prefix, namespace in value.items():
            if not prefix or not urlsplit(namespace).scheme or not namespace.endswith(("/", "#")):
                raise ValueError(f"invalid namespace for prefix {prefix!r}: {namespace!r}")
        return value

    def mapping_file_path(self, root: Path) -> Path:
        """Return the mapping CSV path resolved against `root`; existence is not checked."""
        return root / self.mapping_file

    def metadata_file_path(self, root: Path) -> Path:
        """Return the CSVW metadata path resolved against `root`; existence is not checked."""
        return root / self.metadata_file


class MappingSetsConfig(BaseModel):
    """Validated mapping-set catalogue.

    This is the root of `mapping-sets.yaml`.

    Attributes:
        mapping_sets: Mapping-set configurations by key. The key names built
            artifacts and reports, so it must be a portable path segment:
            lowercase letters, digits, `.`, `_`, and `-`, starting with a letter
            or digit, not ending in `.`, and not a reserved Windows device name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mapping_sets: dict[str, MappingSetConfig]

    @model_validator(mode="after")
    def validate_mapping_set_keys(self) -> MappingSetsConfig:
        """Require every key to be a portable lowercase path segment.

        Raises:
            ValueError: If a key is not a portable lowercase path segment.
        """
        for key in self.mapping_sets:
            validate_portable_source_name(key)
        return self

    def get(self, key: str) -> MappingSetConfig:
        """Return a configured mapping set.

        Raises:
            ConfigurationError: If `key` is not configured. The message lists
                the known keys.
        """
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

    When `ontology_sources` is given, every ontology binding is resolved.

    Args:
        path: Path to `mapping-sets.yaml`, relative to `root` unless absolute.
        root: Workspace root for relative paths. Defaults to the current directory.
        ontology_sources: Loaded ontology source registry. Every `ontologies`
            binding must name a source in it.

    Returns:
        The validated mapping-set catalogue.

    Raises:
        ConfigurationError: If the YAML cannot be read or is invalid, a
            referenced file does not exist, or a bound ontology source is not
            configured.
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
