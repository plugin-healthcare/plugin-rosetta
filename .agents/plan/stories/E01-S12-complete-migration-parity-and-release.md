# E01-S12 Story: complete migration parity and release

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **plugin-rosetta user**,
I want **a released package whose retained workflows match `sssom-rosetta` semantics, with a documented capability matrix and a runnable example**,
so that **I can switch to `plugin-rosetta` knowing exactly what is migrated, what changed, and what is deferred**.

## Value

Migration is only finished when the replacement is proven, installable, and documented.

This story closes the epic by comparing outputs, naming every difference, and shipping something a new user can run.

## Prerequisites

- [E01-S11 Compare local artifact versions](E01-S11-compare-local-artifact-versions.md), and through it every earlier story.

## Scope

### In scope

- A workflow-by-workflow parity comparison between `sssom-rosetta` and `plugin-rosetta`.
- Semantic equivalence of open-format outputs, or an approved documented difference.
- A published capability matrix of migrated sources, formats, and deferred behaviour.
- Completion and review of the CLI command surface over application functions.
- A README quickstart and a runnable example.
- A clean-environment wheel build and install check.
- One named replacement test per retained legacy workflow.

### Out of scope

- Any new capability, format, or source.
- Anything on the deferred list, including FHIR runtime work, a UI, SQL on FHIR, Ariadne, remote storage, and visualisation exports.
- Publishing to a package index, which is a separate release decision.

## Acceptance Criteria

- [ ] GIVEN the retained `sssom-rosetta` workflows, WHEN the parity comparison runs, THEN every retained workflow is listed with its `plugin-rosetta` replacement command and its replacement test name.
- [ ] GIVEN the preserved `omop-onz-g` mapping set and a pinned `sssom-rosetta` revision, WHEN the automated parity test builds SSSOM/TSV and Turtle with both projects, THEN the outputs are semantically equivalent: the same 8 mappings, the same metadata fields, and the same triples.
- [ ] GIVEN any difference found in the comparison, WHEN the release is assessed, THEN each difference is either removed or recorded as an approved, dated, justified entry in the capability matrix.
- [ ] GIVEN a vocabulary graph built from the same ingested release by both projects, WHEN the outputs are compared, THEN the triple sets are equivalent or every difference is an approved documented entry.
- [ ] GIVEN the CLI, WHEN the command surface is reviewed, THEN every command delegates to an application function and no command body contains parsing, validation, graph, or serialisation logic.
- [ ] GIVEN a clean environment with no project checkout on the path, WHEN the built wheel is installed, THEN `rosetta --help` runs and the example completes successfully.
- [ ] GIVEN the README quickstart, WHEN a new user follows it end to end, THEN they install the package, validate the preserved mapping set, build its artifacts, and read the report.
- [ ] GIVEN the runnable example, WHEN it runs on a clean checkout without any licensed release, THEN it completes using only tracked content and produces open-format outputs.
- [ ] GIVEN the capability matrix, WHEN it is read, THEN it lists every migrated source, every published format, every explicitly deferred behaviour, and every non-migrated legacy module with its reason.
- [ ] GIVEN every published output format, WHEN it is read by a standard tool in a process that does not import `plugin_rosetta`, THEN it parses and yields the expected content.
- [ ] GIVEN the release candidate, WHEN `tara check` runs, THEN it passes.

## Technical Tasks

- [ ] Build the retained-workflow inventory from `sssom-rosetta/justfile` recipes and `src/sssom_rosetta/cli.py` commands, excluding the deferred `protege` and `gephi` workflows.
- [ ] For each retained workflow, name the replacement command and the replacement test, and add the test if it does not exist yet.
- [ ] Add an executable parity test that runs both projects at pinned revisions over the preserved mapping set and compares parsed SSSOM/TSV metadata and rows plus Turtle triple sets, treating ordering and formatting differences as equivalent and value differences as failures.
- [ ] Run both projects over one ingested vocabulary release per migrated source and compare triple sets by the same rule.
- [ ] Record each finding as removed or approved in `docs/capability-matrix.md`, with the reason and the approver.
- [ ] Review every CLI command for thinness and move leftover logic into the owning public feature package.
- [ ] Add `examples/build_preserved_mapping_set.py` that validates, builds, and reports the tracked `omop-onz-g` mapping set using only tracked content.
- [ ] Add a README quickstart covering install, validate, build, report, and where outputs land.
- [ ] Build the wheel and install it in a clean environment, then run `rosetta --help` and the example from that environment.
- [ ] Add `tests/test_parity.py` asserting that every retained workflow in the inventory has a replacement test, so the matrix cannot silently drift.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `sssom-rosetta/justfile` recipes `fetch`, `validate`, `build`, `report`, `docs-pages`, `vocab-ingest`, `vocab-build-*`, `vocab-merge` | `justfile` plus `docs/capability-matrix.md` | Each retained recipe needs a named replacement command and test |
| `sssom-rosetta/justfile` recipes `protege`, `gephi-ontology`, `gephi-vocabulary` | `docs/capability-matrix.md` | Recorded as deferred, not migrated |
| `src/sssom_rosetta/mapping/gephi.py`, `src/sssom_rosetta/mapping/protege.py` | `docs/capability-matrix.md` | The only two legacy modules with no target module |
| `sssom-rosetta/tests/test_cli.py` | `tests/test_cli.py` plus per-story command tests | Command coverage is distributed across the owning stories, then checked as a whole here |
| `sssom-rosetta/README.md` | `README.md` | Rewrite the quickstart for the new commands and the tracked registry layout |

## Edge Cases

- Turtle serialisation order and prefix choice differ between libraries, so equivalence must be compared on triple sets rather than file bytes.
- The SSSOM/TSV YAML header field order can differ, so comparison must be on parsed metadata rather than raw text.
- The test must record the `sssom-rosetta` revision it executes so a moving legacy branch cannot silently change the expected output.
- The legacy `mapping_set_id` and `author_label` decisions from E01-S02 will show up as intentional differences and must appear in the matrix rather than as failures.
- A vocabulary comparison needs a licensed release, so it runs on the curator machine and only counts and findings are recorded in the repository.
- A clean-environment install can accidentally pick up the working checkout through the current directory, so the check must run from an unrelated directory.
- The example must not require an ontology download or a licensed release, otherwise a new user cannot run it.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest` passes for the whole suite, including `tests/test_parity.py`.
- [ ] `uv run tara check` passes.
- [ ] `README.md`, `docs/capability-matrix.md`, and `registry/README.md` are current, and the runnable example under `examples/` works.
- [ ] Every published format is proven readable by a standard tool in a process that does not import `plugin_rosetta`.
- [ ] Acceptance criteria verified with the mapping and vocabulary curators, including sign-off on every approved documented difference.
- [ ] No licensed data, cached downloads, generated artifacts, or credentials are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

Parity means equivalent semantics, not identical bytes.

Anything that cannot be made equivalent is a documented decision with an owner, not an open defect carried into the release.
