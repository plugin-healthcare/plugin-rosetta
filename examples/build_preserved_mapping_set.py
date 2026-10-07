"""Build and inspect the tracked mapping set without downloads or licensed data."""

import json
import tempfile
from pathlib import Path

from rdflib import Graph

from plugin_rosetta.mapping import build_mapping_artifacts, report_mapping_set
from plugin_rosetta.utils.io.sssom import read_sssom_tsv


def main() -> None:
    """Build the preserved example and print a machine-readable summary."""
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as temporary:
        output_dir = Path(temporary)
        sssom_path, turtle_path = build_mapping_artifacts("omop-onz-g", output_dir=output_dir, root=root)
        _markdown_path, html_path = report_mapping_set("omop-onz-g", output_dir=output_dir, root=root)
        summary = {
            "mapping_count": len(read_sssom_tsv(sssom_path).mappings or []),
            "report_formats": sorted(("markdown", html_path.suffix.removeprefix("."))),
            "triple_count": len(Graph().parse(turtle_path, format="turtle")),
        }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
