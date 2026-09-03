"""Atomic file replacement."""

import os
import tempfile
from pathlib import Path

from plugin_rosetta.core.errors import RosettaIOError


def atomic_write_text(destination: Path, content: str) -> None:
    """Replace a text file only after its complete content is durable."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(destination)
    except OSError as error:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        raise RosettaIOError(f"Cannot write {destination}: {error}") from error


def atomic_write_bytes(destination: Path, content: bytes) -> None:
    """Replace a binary file only after its complete content is durable."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(destination)
    except OSError as error:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        raise RosettaIOError(f"Cannot write {destination}: {error}") from error
