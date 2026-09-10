from pathlib import Path

import pytest

OMOP_TERMS = (
    "Person",
    "Provider",
    "CareSite",
    "Location",
    "Death",
    "Measurement",
    "PayerPlanPeriod",
    "Vocabulary",
)
ONZ_G_TERMS = (
    "PatientInCare",
    "Caregiver",
    "CareOrganization",
    "Address",
    "Dead",
    "AssessingEvent",
    "InsurancePolicy",
    "ClassificationSystem",
)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent


def _write_ontology(path: Path, prefix: str, namespace: str, terms: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    declarations = "\n".join(f"{prefix}:{term} a owl:Class ." for term in terms)
    path.write_text(
        f"@prefix {prefix}: <{namespace}> .\n@prefix owl: <http://www.w3.org/2002/07/owl#> .\n\n{declarations}\n",
        encoding="utf-8",
    )


@pytest.fixture
def ontology_cache(tmp_path: Path) -> Path:
    """Populate a cache with synthetic stand-ins for the two bound ontologies.

    The fixtures declare exactly the terms the preserved mapping set references,
    so referential validation is exercised without staging or downloading a real
    ontology payload.
    """
    cache_dir = tmp_path / "ontologies"
    _write_ontology(
        cache_dir / "omop-cdm" / "5.4" / "ontology.ttl",
        "omop",
        "https://w3id.org/omop/ontology/",
        OMOP_TERMS,
    )
    _write_ontology(
        cache_dir / "onz-g" / "2.8.1" / "ontology.ttl",
        "onzg",
        "http://purl.org/ozo/onz-g#",
        ONZ_G_TERMS,
    )
    return cache_dir


@pytest.fixture
def drifted_ontology_cache(ontology_cache: Path) -> Path:
    """Return a cache whose OMOP ontology has lost one mapped term."""
    _write_ontology(
        ontology_cache / "omop-cdm" / "5.4" / "ontology.ttl",
        "omop",
        "https://w3id.org/omop/ontology/",
        OMOP_TERMS[:-1],
    )
    return ontology_cache
