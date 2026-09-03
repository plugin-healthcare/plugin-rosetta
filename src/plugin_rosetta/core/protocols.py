"""Structural contracts shared by tested vertical slices."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from plugin_rosetta.core.report import ValidationReport


@runtime_checkable
class Reader[SourceT, ResultT](Protocol):
    """Read a value from a source."""

    def read(self, source: SourceT) -> ResultT:
        """Read the source."""
        ...


@runtime_checkable
class Writer[ValueT, DestinationT](Protocol):
    """Write a value to a destination."""

    def write(self, value: ValueT, destination: DestinationT) -> None:
        """Write the value."""
        ...


@runtime_checkable
class Validator[ValueT](Protocol):
    """Validate a value without changing it."""

    def validate(self, value: ValueT) -> ValidationReport:
        """Validate the value."""
        ...
