import hashlib
import io
import zipfile
from typing import TYPE_CHECKING

import pytest

from plugin_rosetta.config.vocabulary_sources import VocabularySource
from plugin_rosetta.core.errors import VocabularyChecksumError, VocabularyIngestError
from plugin_rosetta.core.report import IssueSeverity
from plugin_rosetta.vocabulary.ingest import cache_dir_for, find_file, ingest_zip

if TYPE_CHECKING:
    from pathlib import Path


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _write_zip(tmp_path: Path, files: dict[str, str]) -> tuple[Path, str]:
    content = _zip_bytes(files)
    path = tmp_path / "release.zip"
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def _source(*, checksum: str | None = None, format_version: str | None = None) -> VocabularySource:
    return VocabularySource(
        name="sample",
        version="1.0",
        kind="rf2",
        description="Synthetic source.",
        download_page="https://example.org/download",
        checksum=checksum,
        format_version=format_version,
    )


def test_ingest_extracts_checksum_verified_release(tmp_path: Path) -> None:
    zip_path, digest = _write_zip(tmp_path, {"Snapshot/Terminology/concepts.txt": "id\n100001\n"})
    cache_dir = tmp_path / "cache"

    result = ingest_zip(_source(checksum=digest), zip_path, cache_dir=cache_dir)

    assert result.path == cache_dir / "sample" / "1.0"
    assert (result.path / "Snapshot/Terminology/concepts.txt").is_file()
    assert result.issue is None


def test_missing_checksum_reports_computed_digest(tmp_path: Path) -> None:
    zip_path, digest = _write_zip(tmp_path, {"concepts.txt": "id\n100001\n"})

    result = ingest_zip(_source(), zip_path, cache_dir=tmp_path / "cache")

    assert result.issue is not None
    assert result.issue.severity is IssueSeverity.WARNING
    assert digest in result.issue.message


def test_checksum_mismatch_leaves_cache_untouched(tmp_path: Path) -> None:
    zip_path, digest = _write_zip(tmp_path, {"concepts.txt": "id\n100001\n"})
    cache_dir = tmp_path / "cache"

    with pytest.raises(VocabularyChecksumError, match=rf"sample.*expected {'0' * 64}.*actual {digest}"):
        ingest_zip(_source(checksum="0" * 64), zip_path, cache_dir=cache_dir)

    assert not cache_dir.exists()


def test_ingest_reuses_populated_cache_without_reading_zip(tmp_path: Path) -> None:
    zip_path, digest = _write_zip(tmp_path, {"concepts.txt": "first"})
    source = _source(checksum=digest)
    cache_dir = tmp_path / "cache"
    first = ingest_zip(source, zip_path, cache_dir=cache_dir)
    zip_path.unlink()

    second = ingest_zip(source, zip_path, cache_dir=cache_dir)

    assert second.path == first.path
    assert (second.path / "concepts.txt").read_text() == "first"


def test_force_replaces_populated_cache(tmp_path: Path) -> None:
    first_zip, _ = _write_zip(tmp_path, {"old.txt": "old"})
    cache_dir = tmp_path / "cache"
    ingest_zip(_source(), first_zip, cache_dir=cache_dir)
    second_zip, _ = _write_zip(tmp_path, {"new.txt": "new"})

    result = ingest_zip(_source(), second_zip, cache_dir=cache_dir, force=True)

    assert not (result.path / "old.txt").exists()
    assert (result.path / "new.txt").read_text() == "new"


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("missing.zip", None, "ZIP not found"),
        ("invalid.zip", b"not a zip", "Not a valid ZIP"),
    ],
)
def test_invalid_input_leaves_cache_untouched(
    tmp_path: Path,
    filename: str,
    content: bytes | None,
    message: str,
) -> None:
    zip_path = tmp_path / filename
    if content is not None:
        zip_path.write_bytes(content)
    cache_dir = tmp_path / "cache"

    with pytest.raises(VocabularyIngestError, match=message):
        ingest_zip(_source(), zip_path, cache_dir=cache_dir)

    assert not cache_dir.exists()


@pytest.mark.parametrize("member", ["../escape.txt", "/absolute.txt", r"..\escape.txt"])
def test_ingest_rejects_unsafe_archive_members(tmp_path: Path, member: str) -> None:
    zip_path, _ = _write_zip(tmp_path, {member: "escape"})

    with pytest.raises(VocabularyIngestError, match="unsafe archive member"):
        ingest_zip(_source(), zip_path, cache_dir=tmp_path / "cache")

    assert not (tmp_path / "escape.txt").exists()


def test_format_version_mismatch_names_expected_and_found_markers(tmp_path: Path) -> None:
    zip_path, _ = _write_zip(
        tmp_path,
        {"thesauri/DT/release_uitleverformaat5.0/table.csv": "id\n1\n"},
    )

    with pytest.raises(
        VocabularyIngestError,
        match=r"expected.*uitleverformaat4\.3.*found.*uitleverformaat5\.0",
    ):
        ingest_zip(
            _source(format_version="uitleverformaat4.3"),
            zip_path,
            cache_dir=tmp_path / "cache",
        )


@pytest.mark.parametrize("found", ["uitleverformaat4.30", "uitleverformaat4.3.1"])
def test_format_version_requires_an_exact_marker(tmp_path: Path, found: str) -> None:
    zip_path, _ = _write_zip(tmp_path, {f"thesauri/DT/release_{found}/table.csv": "id\n1\n"})

    with pytest.raises(VocabularyIngestError, match=rf"expected.*uitleverformaat4\.3.*found.*{found}"):
        ingest_zip(
            _source(format_version="uitleverformaat4.3"),
            zip_path,
            cache_dir=tmp_path / "cache",
        )


def test_cache_dir_rejects_source_name_traversal(tmp_path: Path) -> None:
    source = _source().model_copy(update={"name": "../../outside"})

    with pytest.raises(VocabularyIngestError, match="outside cache root"):
        cache_dir_for(source, tmp_path / "cache")


def test_cache_dir_for_uses_source_name_and_version(tmp_path: Path) -> None:
    assert cache_dir_for(_source(), tmp_path) == tmp_path / "sample" / "1.0"


def test_find_file_filters_by_name_and_path_fragment(tmp_path: Path) -> None:
    snapshot = tmp_path / "Snapshot/Terminology"
    full = tmp_path / "Full/Terminology"
    snapshot.mkdir(parents=True)
    full.mkdir(parents=True)
    expected = snapshot / "sct2_Concept_Snapshot_INT_20260101.txt"
    expected.write_text("snapshot")
    (full / "sct2_Concept_Full_INT_20260101.txt").write_text("full")

    result = find_file(tmp_path, prefix="sct2_Concept_", suffix=".txt", contains="/Snapshot/")

    assert result == expected


def test_find_file_reports_no_match(tmp_path: Path) -> None:
    with pytest.raises(VocabularyIngestError, match=r"No file matching.*CONCEPT.*\.csv"):
        find_file(tmp_path, prefix="CONCEPT", suffix=".csv")


def test_find_file_lists_ambiguous_matches(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")

    with pytest.raises(VocabularyIngestError) as error:
        find_file(tmp_path, suffix=".txt")

    assert str(first) in str(error.value)
    assert str(second) in str(error.value)
