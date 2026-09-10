"""Project-specific vocabulary adapters behind a shared build contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from plugin_rosetta.errors import VocabularyError
from plugin_rosetta.vocabulary._graph_io import write_turtle
from plugin_rosetta.vocabulary.adapters.omop import (
    build_graph as build_omop_model,
)
from plugin_rosetta.vocabulary.adapters.omop import (
    load_relationship_types,
    load_relationships,
    load_target_concepts,
)
from plugin_rosetta.vocabulary.adapters.thesaurus import build_from_release as build_dhd_from_release
from plugin_rosetta.vocabulary.config import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract
from plugin_rosetta.vocabulary.ingest import find_file
from plugin_rosetta.vocabulary.namespaces import PREFIX_MAP
from plugin_rosetta.vocabulary.provenance import write_provenance

if TYPE_CHECKING:
    from pathlib import Path

    from maplib import Model

    from plugin_rosetta.vocabulary.config import ReleaseTable, VocabularySource


class BuildAdapter(Protocol):
    """Build a configured vocabulary graph and its provenance sidecar."""

    @property
    def source_name(self) -> str:
        """Return the configured vocabulary source name."""
        ...

    def build(
        self,
        release_dir: Path,
        output_dir: Path,
        *,
        config_path: Path,
        as_of: str | None,
    ) -> tuple[Path, Path]:
        """Build graph artifacts from one ingested release."""
        ...


def _required_table(source: VocabularySource, role: str) -> ReleaseTable:
    try:
        return next(table for table in source.tables if table.role == role)
    except StopIteration as error:
        raise VocabularyError(f"Vocabulary source {source.name!r} has no required table role {role!r}") from error


def _find_table(release_dir: Path, table: ReleaseTable) -> Path:
    return find_file(
        release_dir,
        name=table.name,
        prefix=table.prefix,
        suffix=table.suffix,
        contains=table.contains,
    )


def _write(
    model: Model,
    output_dir: Path,
    filename: str,
    source: VocabularySource,
    *,
    as_of: str | None,
) -> tuple[Path, Path]:
    turtle_path = write_turtle(
        model,
        output_dir / filename,
        prefixes={prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()}
        | {"skos": "http://www.w3.org/2004/02/skos/core#"},
    )
    metadata_path = write_provenance(
        turtle_path,
        source_name=source.name,
        source_version=source.version,
        format_version=source.format_version,
        as_of=as_of,
    )
    return turtle_path, metadata_path


@dataclass(frozen=True)
class OmopBuildAdapter:
    """Build OMOP graphs through the shared artifact contract."""

    source_name: str = "omop"

    def build(
        self,
        release_dir: Path,
        output_dir: Path,
        *,
        config_path: Path,
        as_of: str | None,
    ) -> tuple[Path, Path]:
        """Build OMOP graph artifacts from an Athena release."""
        if as_of is not None:
            raise VocabularyError("OMOP builds do not accept an as-of date")
        if not release_dir.is_dir() or not any(path.is_file() for path in release_dir.rglob("*")):
            raise VocabularyError(
                f"No ingested OMOP release at {release_dir}. Run 'rosetta vocabulary ingest omop <zip>' first."
            )
        source = load_vocabulary_sources(config_path).get(self.source_name)
        registry_root = config_path.parent.parent
        concept_table = _required_table(source, "concept")
        relationship_table = _required_table(source, "concept-relationship")
        type_table = _required_table(source, "relationship")
        concepts = load_target_concepts(
            _find_table(release_dir, concept_table),
            concept_table,
            load_table_contract(registry_root / concept_table.contract),
        )
        relationships = load_relationships(
            _find_table(release_dir, relationship_table),
            relationship_table,
            load_table_contract(registry_root / relationship_table.contract),
            concepts["concept_id"],
        )
        relationship_types = load_relationship_types(
            _find_table(release_dir, type_table),
            type_table,
            load_table_contract(registry_root / type_table.contract),
        )
        return _write(
            build_omop_model(concepts, relationships, relationship_types),
            output_dir,
            "omop.ttl",
            source,
            as_of=None,
        )


@dataclass(frozen=True)
class DhdBuildAdapter:
    """Build one DHD thesaurus through the shared artifact contract."""

    thesaurus: Literal["dt", "vt"]
    source_name: str = "dhd-thesauri"

    def build(
        self,
        release_dir: Path,
        output_dir: Path,
        *,
        config_path: Path,
        as_of: str | None,
    ) -> tuple[Path, Path]:
        """Build DHD graph artifacts for this adapter's thesaurus."""
        if as_of is None:
            raise VocabularyError("DHD builds require an explicit as-of date")
        source = load_vocabulary_sources(config_path).get(self.source_name)
        model = build_dhd_from_release(
            release_dir,
            self.thesaurus,
            source,
            config_path.parent.parent,
            as_of=as_of,
        )
        label = "diagnosethesaurus" if self.thesaurus == "dt" else "verrichtingenthesaurus"
        return _write(model, output_dir, f"dhd-{label}.ttl", source, as_of=as_of)


_ADAPTERS: dict[str, BuildAdapter] = {
    "omop": OmopBuildAdapter(),
    "dhd-diagnosethesaurus": DhdBuildAdapter("dt"),
    "dhd-verrichtingenthesaurus": DhdBuildAdapter("vt"),
}


def get_build_adapter(name: str) -> BuildAdapter:
    """Return a configured graph-build adapter by public target name."""
    try:
        return _ADAPTERS[name]
    except KeyError as error:
        known = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"Unknown build adapter {name!r}. Known build adapters: {known}") from error
