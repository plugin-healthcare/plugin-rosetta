"""Public package error hierarchy."""


class RosettaError(Exception):
    """Base exception for plugin-rosetta."""


class ConfigurationError(RosettaError):
    """Raised when configuration cannot be loaded or validated."""


class ValidationError(RosettaError):
    """Raised when input does not satisfy a required contract."""


class UnresolvableCurieError(ValidationError):
    """Raised when a CURIE expands to an IRI that its ontology graph does not describe."""

    def __init__(self, curie: str, iri: str) -> None:
        """Name both the authored CURIE and the IRI it expanded to."""
        super().__init__(f"CURIE {curie!r} (expands to {iri!r}) was not found in the ontology graph")


class RosettaIOError(RosettaError):
    """Raised when an input or output operation fails."""


class VocabularyError(RosettaError):
    """Base exception for vocabulary release operations."""


class VocabularyIngestError(VocabularyError):
    """Raised when a vocabulary release cannot be safely ingested."""


class VocabularyChecksumError(VocabularyError):
    """Raised when a vocabulary release does not match its pinned checksum."""
