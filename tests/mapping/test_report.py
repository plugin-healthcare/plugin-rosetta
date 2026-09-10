from plugin_rosetta.mapping import read_mapping_set
from plugin_rosetta.mapping.report import diff_mapping_sets, predicate_counts, render_html, render_markdown


def test_diff_reports_added_removed_and_changed_rows(project_root) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=project_root).mapping_set
    base = mapping_set.model_copy(deep=True)
    head = mapping_set.model_copy(deep=True)
    assert head.mappings is not None
    changed = head.mappings[0].model_copy(update={"comment": "changed"})
    added = head.mappings[1].model_copy(update={"subject_id": "omop:Added"})
    head.mappings = [changed, *head.mappings[2:], added]

    difference = diff_mapping_sets(base, head)

    assert [mapping.subject_id for mapping in difference.added] == ["omop:Added"]
    assert [mapping.subject_id for mapping in difference.removed] == ["omop:Provider"]
    assert [change.after.subject_id for change in difference.changed] == ["omop:Person"]


def test_report_renders_predicate_counts_as_markdown_and_html(project_root) -> None:
    mapping_set = read_mapping_set("omop-onz-g", root=project_root).mapping_set

    counts = predicate_counts(mapping_set)
    markdown = render_markdown(mapping_set)
    html = render_html(markdown)

    assert counts == {
        "skos:broadMatch": 5,
        "skos:exactMatch": 1,
        "skos:narrowMatch": 1,
        "skos:relatedMatch": 1,
    }
    assert "| Predicate | Count |" in markdown
    assert "<table>" in html
    assert "<td>skos:broadMatch</td>" in html
