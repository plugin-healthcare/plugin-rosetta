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
    mo.md("""
    # Rosetta quickstart

    Reads the `omop-onz-g` mapping set through the graph-free `plugin_rosetta`
    application layer, validates it, builds SSSOM/TSV and RDF/Turtle
    artifacts, and renders a Markdown/HTML report. It also builds OMOP and DHD
    vocabulary graphs from synthetic fixtures. These are the same steps as
    the corresponding `rosetta` commands, run interactively.
    """)
    return


@app.cell
def _():
    from pathlib import Path

    from plugin_rosetta.mapping import read_mapping_set

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
    mo.md("""
    ## Building portable artifacts
    """)
    return


@app.cell
def _(MAPPING_SET_KEY, Path, ROOT):
    import tempfile

    from plugin_rosetta.mapping import build_mapping_artifacts, report_mapping_set

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


@app.cell
def _(mo):
    mo.md("""
    ## Building an OMOP vocabulary graph

    This example uses synthetic Athena tables, so it runs offline without a licensed vocabulary
    release. Replace `synthetic_release` with an ingested release directory to inspect curator
    data locally.
    """)
    return


@app.cell
def _(Path, ROOT):
    import json as _json
    import tempfile as _tempfile

    from rdflib import Graph as _Graph

    from plugin_rosetta.vocabulary import build_omop_graph

    synthetic_release = ROOT / "tests/fixtures/vocabulary/athena"
    with _tempfile.TemporaryDirectory() as _omop_tmp:
        omop_turtle_path, omop_metadata_path = build_omop_graph(
            synthetic_release,
            Path(_omop_tmp),
            config_path=ROOT / "registry/config/vocabulary-sources.yaml",
        )
        omop_turtle = omop_turtle_path.read_text()
        omop_metadata_json = _json.dumps(
            _json.loads(omop_metadata_path.read_text()),
            indent=2,
        )
    omop_triple_count = len(_Graph().parse(data=omop_turtle, format="turtle"))
    return (
        omop_metadata_json,
        omop_triple_count,
        omop_turtle,
        synthetic_release,
    )


@app.cell
def _(mo, omop_metadata_json, omop_triple_count, synthetic_release):
    mo.md(
        f"""
        Built **{omop_triple_count} triples** from `{synthetic_release}`.

        Provenance:

        ```json
        {omop_metadata_json}
        ```
        """
    )
    return


@app.cell
def _(mo, omop_turtle):
    mo.md(f"""### OMOP vocabulary Turtle\n\n```turtle\n{omop_turtle}\n```""")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Building DHD thesaurus graphs

    Both examples use synthetic quoted CSV releases. The explicit `as_of` value makes validity
    filtering reproducible and is recorded in each provenance sidecar.
    """)
    return


@app.cell
def _(Path, ROOT):
    import tempfile as _tempfile

    from rdflib import Graph as _Graph

    from plugin_rosetta.vocabulary import build_dhd_graph

    synthetic_dhd_release = ROOT / "tests/fixtures/vocabulary/dhd"
    with _tempfile.TemporaryDirectory() as _dhd_tmp:
        dhd_output = Path(_dhd_tmp)
        dt_path, _dt_metadata = build_dhd_graph(
            synthetic_dhd_release,
            dhd_output,
            "dt",
            as_of="20260910",
            config_path=ROOT / "registry/config/vocabulary-sources.yaml",
        )
        vt_path, _vt_metadata = build_dhd_graph(
            synthetic_dhd_release,
            dhd_output,
            "vt",
            as_of="20260910",
            config_path=ROOT / "registry/config/vocabulary-sources.yaml",
        )
        dt_turtle = dt_path.read_text()
        vt_turtle = vt_path.read_text()
    dhd_counts = {
        "Diagnosethesaurus": len(_Graph().parse(data=dt_turtle, format="turtle")),
        "Verrichtingenthesaurus": len(_Graph().parse(data=vt_turtle, format="turtle")),
    }
    return dhd_counts, dt_turtle


@app.cell
def _(dhd_counts, mo):
    mo.md(
        f"""
        Built **{dhd_counts["Diagnosethesaurus"]} diagnosis triples** and
        **{dhd_counts["Verrichtingenthesaurus"]} procedure triples**.
        """
    )
    return


@app.cell
def _(dt_turtle, mo):
    mo.md(f"""### DHD Diagnosethesaurus Turtle\n\n```turtle\n{dt_turtle}\n```""")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Building and merging RF2 graphs

    The synthetic RF2 fixture contains active and inactive concepts, preferred
    terms, synonyms, and is-a relationships. Both configured RF2 sources use
    the same content here so their shared SNOMED identifiers also demonstrate
    duplicate collapse during merge.
    """)
    return


@app.cell
def _(Path, ROOT):
    import tempfile as _tempfile

    from rdflib import Graph as _Graph

    from plugin_rosetta.vocabulary import build_dhd_graph as _build_dhd_graph
    from plugin_rosetta.vocabulary import build_omop_graph as _build_omop_graph
    from plugin_rosetta.vocabulary import build_rf2_graph as _build_rf2_graph
    from plugin_rosetta.vocabulary import merge_built_vocabulary_graphs as _merge_built_vocabulary_graphs

    with _tempfile.TemporaryDirectory() as _vocabulary_tmp:
        vocabulary_output = Path(_vocabulary_tmp)
        vocabulary_config = ROOT / "registry/config/vocabulary-sources.yaml"
        _build_omop_graph(
            ROOT / "tests/fixtures/vocabulary/athena",
            vocabulary_output,
            config_path=vocabulary_config,
        )
        _build_dhd_graph(
            ROOT / "tests/fixtures/vocabulary/dhd",
            vocabulary_output,
            "dt",
            as_of="20260910",
            config_path=vocabulary_config,
        )
        _build_dhd_graph(
            ROOT / "tests/fixtures/vocabulary/dhd",
            vocabulary_output,
            "vt",
            as_of="20260910",
            config_path=vocabulary_config,
        )
        _build_rf2_graph(
            ROOT / "tests/fixtures/vocabulary/rf2",
            vocabulary_output,
            "loinc-snomed",
            config_path=vocabulary_config,
        )
        _build_rf2_graph(
            ROOT / "tests/fixtures/vocabulary/rf2",
            vocabulary_output,
            "snomed-international",
            config_path=vocabulary_config,
        )
        merged_path = _merge_built_vocabulary_graphs(vocabulary_output)
        merged_triple_count = len(_Graph().parse(merged_path, format="turtle"))
    return (merged_triple_count,)


@app.cell
def _(merged_triple_count, mo):
    mo.md(f"""The merged synthetic vocabulary graph contains **{merged_triple_count} triples**.""")
    return


if __name__ == "__main__":
    app.run()
