# E01-S01 Story: establish the installable package and shared contracts

Epic: [E01 rebuild plugin rosetta as a mapping toolbox](../epics/E01-rebuild-plugin-rosetta-as-a-mapping-toolbox.md)

## User Story

As a **plugin-rosetta maintainer**,
I want **a clean checkout of `plugin-rosetta` to install, expose a `rosetta` CLI, and provide the shared error, report, and boundary contracts**,
so that **every later migration slice starts from a working package and a green quality gate instead of a broken scaffold**.

## Value

The repository currently fails to build because `src/plugin-rosetta` is not a valid import package name.

Nothing else can be migrated, tested, or reviewed until installation, the CLI entry point, and the quality gate work.

## Prerequisites

- None; this is the first story in the epic.

## Scope

### In scope

- Replacing `src/plugin-rosetta/` with `src/plugin_rosetta/`.
- Distribution and build configuration: distribution `plugin-rosetta`, import package `plugin_rosetta`, `uv_build` backend, console script `rosetta = "plugin_rosetta.cli:app"`.
- Direct dependency declarations, including Maplib as a core dependency and the exact `sssom-schema` pin.
- A Typer application with help output and no mapping behaviour.
- Empty workspace initialization with caller-owned configuration and no bundled domain registry.
- The package error hierarchy and the shared validation report type.
- Reader, writer, and validator protocols only.
- `justfile` recipes for `install`, `test`, `lint`, `format`, `typecheck`, and `check`.

### Out of scope

- Reading, validating, or writing any mapping, ontology, or vocabulary format.
- Any `registry/` content change.
- Any application service or CLI subcommand beyond the top-level help.

## Acceptance Criteria

- [ ] GIVEN a clean checkout, WHEN `uv sync --all-groups` runs, THEN the build succeeds and `plugin_rosetta` is importable.
- [ ] GIVEN the synced environment, WHEN `uv run rosetta --help` runs, THEN it exits 0 and prints the application help without offering a mapping, ontology, or vocabulary command.
- [ ] GIVEN the synced environment, WHEN `uv run tara check` runs, THEN lint, format, type, test, and security checks all pass.
- [ ] GIVEN the package error hierarchy, WHEN any package error type is raised, THEN it is an instance of the single package base error, so callers can catch one type.
- [ ] GIVEN a validation report with at least one issue, WHEN its validity is inspected, THEN it reports invalid and exposes every issue with a stable identifier, severity, and message.
- [ ] GIVEN a validation report with no issues, WHEN its validity is inspected, THEN it reports valid.
- [ ] GIVEN a trivial in-test implementation of each of the reader, writer, and validator protocols, WHEN it is checked against the protocol, THEN it conforms without inheriting from a package base class.
- [ ] GIVEN `pyproject.toml`, WHEN dependencies are inspected, THEN `maplib`, `rdflib`, `csvw`, `curies`, `linkml-runtime`, `polars`, `pydantic`, `typer`, and an HTTP client are direct dependencies and `sssom-schema` is pinned to `1.1.0a5`.
- [x] GIVEN an installed wheel, WHEN `rosetta init <workspace>` runs, THEN it creates empty source
  catalogues and does not copy healthcare-specific configuration from package data.

## Technical Tasks

- [ ] Delete `src/plugin-rosetta/` and create `src/plugin_rosetta/__init__.py` with the package docstring and version export.
- [ ] Update `pyproject.toml`: add `[project.scripts] rosetta = "plugin_rosetta.cli:app"`, add the direct dependencies listed above, pin `sssom-schema==1.1.0a5`, and keep `maplib` in `[project.dependencies]` rather than behind an extra or a benchmark gate.
- [ ] Add `src/plugin_rosetta/cli.py` with a `typer.Typer` application, a help string, and no subcommands.
- [ ] Add `src/plugin_rosetta/errors.py` with a `RosettaError` base and the first specialisations needed by later stories (`ConfigurationError`, `ValidationError`, `IOError` equivalent named to avoid shadowing the builtin).
- [ ] Add `src/plugin_rosetta/reports.py` with frozen Pydantic `ValidationIssue` (code, severity, location, message) and `ValidationReport` (issues, `is_valid`, merge helper).
- [x] Remove the speculative `Reader`, `Writer`, and `Validator` protocols until a second
  implementation proves a shared contract.
- [ ] Add the `justfile` with `install`, `test`, `lint`, `format`, `typecheck`, and `check` recipes, each a thin `uv run ...` wrapper.
- [ ] Add `tests/test_cli.py`, `tests/test_errors.py`, and `tests/test_reports.py`.
- [ ] Update `README.md` with the install and `rosetta --help` quickstart lines only.
- [x] Keep the repository's healthcare configuration under top-level `registry/` and exclude
  domain source catalogues, schemas, and mappings from `src/plugin_rosetta/`.

## Migration Notes

| Legacy source | Target | Note |
| --- | --- | --- |
| `sssom-rosetta/pyproject.toml` `[project.scripts]` | `pyproject.toml` `[project.scripts]` | Same `rosetta` script name, new module path `plugin_rosetta.cli:app` |
| `sssom-rosetta/pyproject.toml` `sssom-schema==1.1.0a5` | `pyproject.toml` | Pin the exact version before E01-S03 regenerates the model |
| `src/sssom_rosetta/vocabulary/errors.py` (`VocabularyError`) | `src/plugin_rosetta/errors.py` | Generalise into the package-wide base error; the vocabulary-specific subclass returns in E01-S07 |
| `src/sssom_rosetta/cli.py` (`app = typer.Typer(...)`, line 76) | `src/plugin_rosetta/cli.py` | Only the application object and help text move now; commands arrive with their owning story |
| `sssom-rosetta/justfile` `install` recipe | `justfile` | Same `uv sync --all-groups` behaviour |

## Edge Cases

- A stale `src/plugin-rosetta/` directory left behind after the rename would shadow nothing but would still be packaged; the build must fail the test suite if it reappears.
- `uv_build` rejects a distribution and module name mismatch, so the `plugin-rosetta` to `plugin_rosetta` mapping must be explicit in `[tool.uv.build-backend]` or by directory layout.
- `maplib` ships platform wheels; the install check must run on the developer platform in CI-equivalent conditions rather than assuming a source build.
- The protocols must stay unimplemented in this story; adding a fourth protocol before a tested slice needs it is out of scope.

## Definition of Done

- [ ] Every new behaviour was driven by a failing test written first.
- [ ] `uv run pytest tests/test_cli.py tests/test_errors.py tests/test_reports.py` passes.
- [ ] `uv run tara check` passes.
- [ ] `README.md` documents install and `rosetta --help`.
- [ ] No published output format is claimed by this story, so the interoperability requirement is satisfied vacuously and recorded as such in the pull request.
- [ ] Acceptance criteria verified with the maintainer on a clean clone.
- [ ] No licensed data, cached downloads, or generated artifacts are staged.
- [ ] The developer reviews and commits; the agent does not commit or push.

## Notes

The plan deliberately limits this story to protocols and contracts.

Do not add `config/`, `io/`, `mapping/`, `ontology/`, `vocabulary/`, `graph/`, `artifacts/`, or `application/` modules until the story that needs them.

ADR-0003 supersedes the later packaged-starter decision from ADR-0001. Workspace initialization is
generic library behavior; the repository registry remains example project input.
