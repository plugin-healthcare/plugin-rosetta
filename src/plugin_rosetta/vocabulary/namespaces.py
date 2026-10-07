"""Shared namespaces and IRI minting for vocabulary graphs."""

from dataclasses import dataclass
from urllib.parse import quote

from rdflib import Namespace, URIRef


@dataclass(frozen=True)
class VocabularyNamespace:
    """One readable Turtle prefix and its RDF namespace."""

    prefix: str
    namespace: Namespace


_NAMESPACES = (
    VocabularyNamespace("sct", Namespace("http://snomed.info/id/")),
    VocabularyNamespace("omopconcept", Namespace("https://w3id.org/omop/concept/")),
    VocabularyNamespace("loinc", Namespace("https://loinc.org/")),
    VocabularyNamespace("rxnorm", Namespace("http://purl.bioontology.org/ontology/RXNORM/")),
    VocabularyNamespace("icd10", Namespace("http://hl7.org/fhir/sid/icd-10/")),
    VocabularyNamespace("icd10cm", Namespace("http://hl7.org/fhir/sid/icd-10-cm/")),
    VocabularyNamespace("dhddt", Namespace("https://w3id.org/dhd/diagnosethesaurus/concept/")),
    VocabularyNamespace("dhdvt", Namespace("https://w3id.org/dhd/verrichtingenthesaurus/concept/")),
    VocabularyNamespace("dbc", Namespace("https://w3id.org/dhd/dbc/")),
)

PREFIX_MAP = {entry.prefix: entry.namespace for entry in _NAMESPACES}
SCT = PREFIX_MAP["sct"]
OMOP_CONCEPT = PREFIX_MAP["omopconcept"]
LOINC = PREFIX_MAP["loinc"]
RXNORM = PREFIX_MAP["rxnorm"]
ICD10 = PREFIX_MAP["icd10"]
ICD10CM = PREFIX_MAP["icd10cm"]
DHD_DIAGNOSETHESAURUS = PREFIX_MAP["dhddt"]
DHD_VERRICHTINGENTHESAURUS = PREFIX_MAP["dhdvt"]
DBC = PREFIX_MAP["dbc"]

THESAURUS_NAMESPACES = {
    "dt": DHD_DIAGNOSETHESAURUS,
    "vt": DHD_VERRICHTINGENTHESAURUS,
}

_VOCABULARY_NAMESPACES = {
    "SNOMED": SCT,
    "LOINC": LOINC,
    "RxNorm": RXNORM,
    "ICD10": ICD10,
    "ICD10CM": ICD10CM,
}

TARGET_VOCABULARIES = frozenset(
    {
        "SNOMED",
        "LOINC",
        "RxNorm",
        "RxNorm Extension",
        "ICD10",
        "ICD10CM",
    }
)


def sct_iri(sctid: str) -> URIRef:
    """Return the canonical SNOMED CT IRI for an SCTID."""
    return SCT[sctid]


def dhd_concept_iri(thesaurus: str, concept_id: str) -> URIRef:
    """Return a DHD concept IRI in the thesaurus-specific namespace."""
    try:
        namespace = THESAURUS_NAMESPACES[thesaurus]
    except KeyError as error:
        known = ", ".join(sorted(THESAURUS_NAMESPACES))
        raise ValueError(f"Unknown DHD thesaurus {thesaurus!r}. Known values: {known}") from error
    return namespace[concept_id]


def dbc_iri(dbc_id: str) -> URIRef:
    """Return a DBC IRI for a specialty-scoped composite identifier."""
    return DBC[dbc_id]


def omop_iri(concept_id: str) -> URIRef:
    """Return the OMOP concept IRI for a concept identifier."""
    return OMOP_CONCEPT[concept_id]


def source_concept_iri(vocabulary_id: str, concept_code: str) -> URIRef | None:
    """Return a native source-vocabulary IRI when one is defined."""
    namespace = _VOCABULARY_NAMESPACES.get(vocabulary_id)
    if namespace is None:
        return None
    return URIRef(f"{namespace}{quote(concept_code, safe='')}")
