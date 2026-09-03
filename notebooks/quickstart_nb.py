import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl

    return mo, pl


@app.cell
def _(mo):
    mo.md(
        """
        # Rosetta mapping quickstart

        Reads the `omop-onz-g` mapping set through the graph-free `plugin_rosetta`
        application layer, validates it, builds SSSOM/TSV and RDF/Turtle
        artifacts, and renders a Markdown/HTML report — the same steps as
        `rosetta mapping validate|build|report`, run interactively.
        """
    )
    return


@app.cell
def _():
    from pathlib import Path

    from plugin_rosetta.application.mapping import read_mapping_set

    ROOT = Path(__file__).resolve().parent.parent
    MAPPING_SET_KEY = "omop-onz-g"

    result = read_mapping_set(MAPPING_SET_KEY, root=ROOT)
    mapping_set = result.mapping_set
    return MAPPING_SET_KEY, Path, ROOT, mapping_set, result


@app.cell
def _(mo, result):
    mo.md(f"""**{len(result.report.issues)} non-fatal input warnings** were recorded while reading the mapping set.""")
    return


@app.cell
def _(mapping_set, pl):
    mappings_df = pl.DataFrame(
        [
            {
                "subject_id": mapping.subject_id,
                "predicate_id": mapping.predicate_id,
                "object_id": mapping.object_id,
                "mapping_justification": mapping.mapping_justification,
                "confidence": mapping.confidence,
            }
            for mapping in mapping_set.mappings or []
        ]
    )
    mappings_df
    return (mappings_df,)


@app.cell
def _(mappings_df, pl):
    mappings_df.group_by("predicate_id").len().sort(by=pl.col("len"), descending=True)
    return


@app.cell
def _(mo):
    mo.md("""## Building portable artifacts""")
    return


@app.cell
def _(MAPPING_SET_KEY, Path, ROOT):
    import tempfile

    from plugin_rosetta.application.mapping import build_mapping_artifacts, report_mapping_set

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        sssom_path, turtle_path = build_mapping_artifacts(MAPPING_SET_KEY, output_dir=output_dir, root=ROOT)
        markdown_path, _html_path = report_mapping_set(MAPPING_SET_KEY, output_dir=output_dir, root=ROOT)
        sssom_text = sssom_path.read_text()
        turtle_text = turtle_path.read_text()
        report_markdown = markdown_path.read_text()
    return report_markdown, sssom_text, turtle_text


@app.cell
def _(mo, sssom_text):
    mo.md(f"""### SSSOM/TSV\n\n```tsv\n{sssom_text}\n```""")
    return


@app.cell
def _(mo, turtle_text):
    mo.md(f"""### RDF/Turtle\n\n```turtle\n{turtle_text}\n```""")
    return


@app.cell
def _(mo, report_markdown):
    mo.md(report_markdown)
    return


if __name__ == "__main__":
    app.run()
