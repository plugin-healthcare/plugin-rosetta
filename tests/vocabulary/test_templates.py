import polars as pl

from plugin_rosetta.vocabulary.templates import LANG_STRING_FIELD, language_tagged_column


def test_language_tagged_column_preserves_values_nulls_and_language() -> None:
    tagged = language_tagged_column(pl.Series("label", ["Concept", None]), language="en")

    assert tagged.struct.field(LANG_STRING_FIELD).to_list() == ["Concept", None]
    assert tagged.struct.field("l").to_list() == ["en", "en"]
