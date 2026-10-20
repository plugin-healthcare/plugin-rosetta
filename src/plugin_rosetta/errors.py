"""Public package error hierarchy.

Expected failures derive from `RosettaError`. Invalid selector arguments in the
vocabulary API raise `ValueError` instead.
"""


class RosettaError(Exception):
    """Base exception for plugin-rosetta.

    Invalid selector arguments in the vocabulary API, such as an unknown DHD
    thesaurus, raise `ValueError` instead.
    """


class ConfigurationError(RosettaError):
    """Raised when configuration cannot be loaded or validated.

    Causes include malformed YAML, invalid fields, unknown mapping-set or
    source names, and configured files that do not exist.
    """


class ValidationError(RosettaError):
    """Raised when input does not satisfy a required contract.

    Examples are a CSV that violates its CSVW metadata, a row that violates the
    SSSOM schema, a checksum mismatch, and a validation report with errors.
    """


class UnresolvableCurieError(ValidationError):
    """Raised when a CURIE expands to an IRI that its ontology graph does not describe.

    The message names both the authored CURIE and the expanded IRI.
    """

    def __init__(self, curie: str, iri: str) -> None:
        """Name both the authored CURIE and the IRI it expanded to.

        Args:
            curie: The CURIE as written by the curator, for example `onz-g:Diagnosis`.
            iri: The absolute IRI that the CURIE expanded to with the mapping set's `curie_map`.
        """
        super().__init__(f"CURIE {curie!r} (expands to {iri!r}) was not found in the ontology graph")


class RosettaIOError(RosettaError):
    """Raised when an input or output operation fails.

    Causes include failed downloads, unreadable or unwritable files, a missing
    or modified ontology cache, and initializing over an existing workspace.
    """


class ArtifactError(RosettaError):
    """Raised when a local artifact operation cannot be completed.

    Causes include invalid names, unreadable artifacts, unknown versions,
    conflicting provenance, and impossible comparisons.
    """


class VocabularyError(RosettaError):
    """Base exception for vocabulary release operations.

    Raised directly when a graph build or merge cannot proceed, for example
    because a table role is not configured or a graph file is missing.
    """


class VocabularyIngestError(VocabularyError):
    """Raised when a vocabulary release cannot be safely ingested.

    Causes include a missing or corrupt ZIP, an unsafe archive member, a
    missing format marker or table, and tables that fail their contracts.
    """


class VocabularyChecksumError(VocabularyError):
    """Raised when a vocabulary release does not match its pinned checksum.

    Also raised when a cached release does not match its integrity manifest.
    """
