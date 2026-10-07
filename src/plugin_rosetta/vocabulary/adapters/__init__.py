"""Project-specific vocabulary adapters behind a shared build contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

import polars as pl
from maplib import Model
from rdflib import Graph

from plugin_rosetta.errors import VocabularyError
from plugin_rosetta.vocabulary._graph_io import write_rdflib_turtle, write_turtle
from plugin_rosetta.vocabulary.adapters.omop import (
    build_graph as build_omop_model,
)
from plugin_rosetta.vocabulary.adapters.omop import (
    load_relationship_types,
    load_relationships,
    load_target_concepts,
)
from plugin_rosetta.vocabulary.adapters.rf2 import build_graph as build_rf2_graph
from plugin_rosetta.vocabulary.adapters.rf2 import omission_counts as rf2_omission_counts
from plugin_rosetta.vocabulary.adapters.rf2 import read_rf2
from plugin_rosetta.vocabulary.adapters.thesaurus import build_from_release as build_dhd_from_release
from plugin_rosetta.vocabulary.config import load_vocabulary_sources
from plugin_rosetta.vocabulary.frames import load_table_contract
from plugin_rosetta.vocabulary.ingest import find_file
from plugin_rosetta.vocabulary.namespaces import PREFIX_MAP, source_concept_iri
from plugin_rosetta.vocabulary.provenance import write_provenance

if TYPE_CHECKING:
    from pathlib import Path

    from plugin_rosetta.vocabulary.config import ReleaseTable, VocabularySource


class BuildAdapter(Protocol):
    """Build a configured vocabulary graph and its provenance sidecar."""

    @property
    def source_name(self) -> str:
        """Return the configured vocabulary source name."""
        ...

    @property
    def output_filename(self) -> str:
        """Return the stable generated Turtle filename."""
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
    model: Model | Graph,
    output_dir: Path,
    filename: str,
    source: VocabularySource,
    *,
    as_of: str | None,
    omissions: dict[str, dict[str, int]] | None = None,
) -> tuple[Path, Path]:
    prefixes = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    }
    destination = output_dir / filename
    if isinstance(model, Model):
        turtle_path = write_turtle(model, destination, prefixes=prefixes)
    else:
        turtle_path = write_rdflib_turtle(model, destination, prefixes=prefixes)
    metadata_path = write_provenance(
        turtle_path,
        source_name=source.name,
        source_version=source.version,
        format_version=source.format_version,
        as_of=as_of,
        omissions=omissions,
    )
    return turtle_path, metadata_path


def _query_height(model: Model, query: str) -> int:
    result = model.query(query)
    if not isinstance(result, pl.DataFrame):
        raise VocabularyError("Expected a tabular result while calculating graph omission counts")
    return result.height


@dataclass(frozen=True)
class OmopBuildAdapter:
    """Build OMOP graphs through the shared artifact contract."""

    source_name: str = "omop"
    output_filename: str = "omop.ttl"

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
        rows = concepts.with_columns(
            _label_missing=concepts["concept_name"].is_null() | (concepts["concept_name"] == ""),
            _code_missing=concepts["concept_code"].is_null() | (concepts["concept_code"] == ""),
        )
        source_missing = sum(
            source_concept_iri(vocabulary_id, concept_code) is None
            for vocabulary_id, concept_code in zip(
                concepts["vocabulary_id"],
                concepts["concept_code"],
                strict=True,
            )
        )
        omissions = {
            "OmopConceptTemplate": {
                "label": int(rows["_label_missing"].sum()),
                "code": int(rows["_code_missing"].sum()),
                "source": source_missing,
            }
        }
        return _write(
            build_omop_model(concepts, relationships, relationship_types),
            output_dir,
            self.output_filename,
            source,
            as_of=None,
            omissions=omissions,
        )


@dataclass(frozen=True)
class DhdBuildAdapter:
    """Build one DHD thesaurus through the shared artifact contract."""

    thesaurus: Literal["dt", "vt"]
    source_name: str = "dhd-thesauri"

    @property
    def output_filename(self) -> str:
        """Return the thesaurus-specific output filename."""
        label = "diagnosethesaurus" if self.thesaurus == "dt" else "verrichtingenthesaurus"
        return f"dhd-{label}.ttl"

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
        concept_count = _query_height(
            model,
            "SELECT ?s WHERE { ?s a <http://www.w3.org/2004/02/skos/core#Concept> }",
        )
        label_count = _query_height(
            model,
            "SELECT ?s WHERE { ?s <http://www.w3.org/2004/02/skos/core#prefLabel> ?o }",
        )
        snomed_count = _query_height(
            model,
            "SELECT ?s WHERE { ?s <http://www.w3.org/2004/02/skos/core#exactMatch> ?o }",
        )
        omissions = {
            "DhdConceptTemplate": {
                "label": concept_count - label_count,
                "snomed": concept_count - snomed_count,
            }
        }
        return _write(
            model,
            output_dir,
            self.output_filename,
            source,
            as_of=as_of,
            omissions=omissions,
        )


@dataclass(frozen=True)
class Rf2BuildAdapter:
    """Build one configured RF2 source graph."""

    source_name: str
    output_filename: str

    def build(
        self,
        release_dir: Path,
        output_dir: Path,
        *,
        config_path: Path,
        as_of: str | None,
    ) -> tuple[Path, Path]:
        """Build graph artifacts from configured RF2 table roles."""
        if as_of is not None:
            raise VocabularyError("RF2 snapshot builds do not accept an as-of date")
        source = load_vocabulary_sources(config_path).get(self.source_name)
        if source.language_refset_id is None:
            raise VocabularyError(f"RF2 source {source.name!r} has no configured language_refset_id")
        registry_root = config_path.parent.parent
        frames = {}
        for role in ("concept", "description", "language", "relationship"):
            table = _required_table(source, role)
            frames[role] = read_rf2(
                _find_table(release_dir, table),
                table,
                load_table_contract(registry_root / table.contract),
            )
        graph = build_rf2_graph(
            frames["concept"],
            frames["description"],
            frames["language"],
            frames["relationship"],
            source.language_refset_id,
        )
        omissions = rf2_omission_counts(
            frames["concept"],
            frames["description"],
            frames["language"],
            frames["relationship"],
            source.language_refset_id,
        )
        return _write(
            graph,
            output_dir,
            self.output_filename,
            source,
            as_of=None,
            omissions=omissions,
        )


_ADAPTERS: dict[str, BuildAdapter] = {
    "omop": OmopBuildAdapter(),
    "dhd-diagnosethesaurus": DhdBuildAdapter("dt"),
    "dhd-verrichtingenthesaurus": DhdBuildAdapter("vt"),
    "loinc-snomed": Rf2BuildAdapter("loinc-snomed", "loinc-snomed.ttl"),
    "snomed-international": Rf2BuildAdapter("snomed-international", "snomed-international.ttl"),
}


def get_build_adapter(name: str) -> BuildAdapter:
    """Return a configured graph-build adapter by public target name."""
    try:
        return _ADAPTERS[name]
    except KeyError as error:
        known = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"Unknown build adapter {name!r}. Known build adapters: {known}") from error


def build_output_paths(output_dir: Path) -> tuple[Path, ...]:
    """Return every registered adapter output path in stable order."""
    return tuple(output_dir / _ADAPTERS[name].output_filename for name in sorted(_ADAPTERS))
