import ast
import json
import subprocess
import sys
from pathlib import Path

from rdflib import Graph

from plugin_rosetta.mapping import build_mapping_artifacts
from plugin_rosetta.utils.io.sssom import read_sssom_tsv

ROOT = Path(__file__).parents[1]
INVENTORY = ROOT / "tests/fixtures/parity/workflows.json"
LEGACY_REVISION = "46fb077c246388f8c692cdcc6b9129a06f669109"


def test_retained_workflow_inventory_is_pinned_and_every_replacement_test_exists() -> None:
    inventory = json.loads(INVENTORY.read_text())

    assert inventory["legacy_revision"] == LEGACY_REVISION
    assert inventory["workflows"]
    for workflow in inventory["workflows"]:
        test_path_text, function_name = workflow["test"].split("::", maxsplit=1)
        test_path = ROOT / test_path_text
        functions = {
            node.name
            for node in ast.parse(test_path.read_text()).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert function_name in functions, workflow


def test_preserved_mapping_build_has_legacy_semantics(tmp_path: Path) -> None:
    sssom_path, turtle_path = build_mapping_artifacts("omop-onz-g", output_dir=tmp_path, root=ROOT)

    mapping_set = read_sssom_tsv(sssom_path)
    assert len(mapping_set.mappings or []) == 8
    assert str(mapping_set.mapping_set_id) == (
        "https://raw.githubusercontent.com/plugin-healthcare/sssom-rosetta/main/build/mappings/omop-onz-g.sssom.tsv"
    )
    assert str(mapping_set.license) == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert len(Graph().parse(turtle_path, format="turtle")) == 8


def test_runnable_example_completes_from_an_unrelated_working_directory(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "examples/build_preserved_mapping_set.py")],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary == {
        "mapping_count": 8,
        "report_formats": ["html", "markdown"],
        "triple_count": 8,
    }
