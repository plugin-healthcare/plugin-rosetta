from typing import TYPE_CHECKING

from plugin_rosetta.core.protocols import Reader, Validator, Writer
from plugin_rosetta.core.report import ValidationReport

if TYPE_CHECKING:
    from pathlib import Path


class TextReader:
    def read(self, source: Path) -> str:
        return source.read_text()


class TextWriter:
    def write(self, value: str, destination: Path) -> None:
        destination.write_text(value)


class TextValidator:
    def validate(self, value: str) -> ValidationReport:
        return ValidationReport()


def test_structural_protocols_need_no_package_base_class() -> None:
    assert isinstance(TextReader(), Reader)
    assert isinstance(TextWriter(), Writer)
    assert isinstance(TextValidator(), Validator)
