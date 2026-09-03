# Foundation and mapping branch handover

## Branch

Work continues on `feature/rosetta-foundation-mapping`.

Nothing has been committed, pushed, or staged.

The initial commit tracked only `.gitignore`, `LICENSE`, and `README.md`, so most of the package scaffold currently appears as untracked content.

## Intended review scope

The first review branch combines the migration plan with E01-S01 through E01-S04:

- Installable `plugin_rosetta` package and shared contracts.
- Validated mapping-set configuration.
- Graph-free CSVW mapping reading.
- Deterministic SSSOM/TSV, RDF/Turtle, Markdown, and HTML output.

Ontology resolution, vocabulary graphs, artifact versioning, FHIR runtime, and remote storage remain outside this branch.

## Planning state

Claude Opus completed and checked one umbrella epic and twelve numbered stories.

The epic is `.agents/plan/epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md`.

The stories are `.agents/plan/stories/E01-S01-*.md` through `.agents/plan/stories/E01-S12-*.md`.

Working epics and stories intentionally override Tara's `docs/` defaults because this repository reserves `docs/` for final documentation.

The SQL on FHIR spike is under `.agents/spike/` and remains deferred.

## Implemented

### E01-S01

- Replaced the invalid `src/plugin-rosetta/` path with `src/plugin_rosetta/`.
- Added the `uv_build` package, `py.typed`, Typer application, `rosetta` script, error hierarchy, validation report, structural protocols, tests, README quickstart, and thin `just` recipes.
- Repaired the duplicate dependency groups and removed copied Nyctea-specific Ruff configuration.
- Added direct dependencies for RDFLib, CSVW, Curies, LinkML Runtime, and HTTPX.
- Pinned `sssom-schema==1.1.0a5` and kept Maplib as a core dependency.

### E01-S02

- Added strict duplicate-key YAML loading.
- Added frozen mapping-set configuration models, explicit root-based path resolution, file checks, IRI and CURIE namespace checks, application lookup, `rosetta mapping list`, and tests.
- Kept the legacy `mapping_set_id` and `author_label` unchanged.
- Documented both retained values as requiring a separate curator-reviewed publication decision.

### E01-S03

- Generated the SSSOM Pydantic model from `sssom-schema==1.1.0a5`.
- Applied the known LinkML generator workaround by importing `linkml_runtime.utils.metamodelcore.URI`.
- Added CSVW typed reading, duplicate primary-key rejection, explicit empty-cell warnings, CURIE expansion, schema-model construction, application orchestration, `rosetta mapping validate`, and preservation tests for all eight mappings.

### E01-S04

- Added atomic text replacement using a temporary file in the destination directory.
- Added deterministic SSSOM/TSV writing and reading.
- Added deterministic RDF/Turtle writing and RDF graph conversion.
- Added mapping differences, predicate counts, Markdown and standalone HTML reports.
- Added `rosetta mapping build`, `rosetta mapping report`, matching `just` recipes, README usage, and tests.
- This slice is implemented but not yet green.

## Current validation state

`tara check` is fully green: lint, format, types, tests, and security (`uv audit`) all pass.

The combined targeted test run and the full `uv run pytest` run both show 33 passed, 0 failed.

The wheel builds cleanly (`uv build`), installs into a clean venv, and `rosetta --help`, `rosetta mapping list`, `rosetta mapping validate omop-onz-g`, `rosetta mapping build`, and `rosetta mapping report` all work from that clean install.

Output was independently verified outside `plugin_rosetta`: `sssom-py` parses the written SSSOM/TSV (8 rows, correct `mapping_set_id`), and RDFLib parses the written Turtle (8 triples).

## Completed since last handover

- Fixed the `tests/io/test_rdf.py` fixture: replaced `mapping_justification="test:manual"` with `semapv:ManualMappingCuration` and added the `semapv` curie_map entry.
- Ran `ruff check --fix` and `ruff format`; fixed the remaining stdlib/first-party `TC001`/`TC003` violations by moving type-only imports under `TYPE_CHECKING` blocks across `application/mapping.py`, `application/mapping_sets.py`, `core/protocols.py`, `io/csvw.py`, `io/rdf.py`, `io/sssom.py`, `io/yaml.py`, `mapping/curies.py`, `mapping/report.py`, `mapping/validate.py`, and two test files. Verified on Python 3.14 (PEP 649 lazy annotations) that `TYPE_CHECKING`-only annotations on dataclass fields do not break `@dataclass`.
- Fixed a real `B007` loop-variable smell in `io/sssom.py` by replacing the `for`/`else` scan with a `next(...)` lookup.
- Fixed `FURB171` in `io/sssom.py` (single-item container membership test) and added a justified `# noqa: S506` with an explanatory comment in `io/yaml.py` for the intentionally safe `_UniqueKeyLoader` (subclasses `yaml.SafeLoader`).
- Ran `uv run ty check .` and fixed all real diagnostics rather than suppressing them:
  - Narrowed `Optional` SSSOM-model fields (`mappings`, `curie_map`, `comment`, `subject_id`/`object_id`) with explicit `is not None`/truthiness checks in both application code (`io/rdf.py::_expanded_triples`) and tests.
  - Hardened `io/csvw.py::read_mapping_rows` with an `isinstance(table, Table)` check and an explicit missing-primary-key check, replacing unchecked `table.tableSchema.primaryKey` access; added a small `_as_row_dict` helper to handle `iterdicts()`'s documented `dict | tuple[str, int, dict]` return union.
  - Added an explicit `import yaml.resolver` in `io/yaml.py` to silence a `possibly-missing-submodule` warning.
  - Replaced a frozen-model direct attribute assignment in `tests/config/test_mapping_sets.py` with a scoped `# ty: ignore[invalid-assignment]` (the assignment is intentionally invalid — the test asserts the frozen model raises at runtime).
  - Added `[tool.ty.src] exclude = ["src/plugin_rosetta/mapping/models/sssom.py"]` to `pyproject.toml`, matching the existing Ruff exclude for the same generated file, instead of hand-patching generated code for one generated-only pydantic serializer typing mismatch.

All of this is implemented but not yet committed, staged, or pushed.

## Start here tomorrow

1. Inspect the complete branch diff and keep unrelated scaffold changes out of the review where possible.
2. Draft the commit message(s) and hand off to the developer for review and commit (per repo policy, do not commit or push directly).
3. Consider whether the branch should be split for review (e.g. foundation vs. mapping-set config vs. CSVW/SSSOM/RDF/report slices) given its combined scope.

## Interactive notebook increment (2026-09-03)

Added `notebooks/quickstart_nb.py`, a marimo notebook ported from the ideas in the old
`sssom-rosetta` `notebooks/omop.py` and `notebooks/sparql.py` (Polars inspection cells),
but rebuilt against this branch's graph-free API instead of the old Maplib-based graph
queries, which are out of scope here.

The notebook reads `omop-onz-g` via `read_mapping_set`, inspects it as a Polars
`DataFrame` (rows, predicate counts), then calls `build_mapping_artifacts` and
`report_mapping_set` to produce the same SSSOM/TSV, Turtle, Markdown, and HTML output as
the CLI, rendering each inline.

Changes to support it:

- Moved the `nb` dependency group from `[project.optional-dependencies]` to
  `[dependency-groups]` and included it in `dev`, so `uv sync --all-groups` installs
  `marimo` (matching the `pluginlake` sibling repo's convention). It was previously
  declared but unreachable from the documented install command.
- Extended the existing `"*_nb.py"` Ruff per-file-ignore with `INP001`, `PLR1711`,
  `N806`, `N803`, and `B018` — all inherent to marimo's generated cell structure (bare
  trailing `return`, non-lowercase notebook constants passed as cell parameters, and a
  cell's trailing expression being its display value), not code smells.
- Added `notebooks/` to `[tool.ty.src] exclude`, matching `pluginlake`'s convention,
  since marimo cell parameters are dynamically typed by design.
- Added `just notebook` (`uv run marimo edit notebooks/quickstart_nb.py`) and a
  README "Explore interactively" section.

Verified by running `uv run marimo export html notebooks/quickstart_nb.py -o ...`
(marimo's non-interactive full-execution path) twice — before and after the Ruff
fixes — and confirming the exported HTML contains real mapping rows, the rendered
SSSOM/TSV, and the rendered Turtle. `tara check` is green with the notebook included.

## Known follow-up points

- The regeneration command in `registry/README.md` does not yet reproduce the manual `URI` import workaround automatically.
- `pyproject.toml` still has the placeholder project description.
- The generated SSSOM model is excluded from Ruff because it is generated code.
- No authored registry values were changed.
- No licensed, cached, or generated mapping payloads were added under `registry/data/`.
