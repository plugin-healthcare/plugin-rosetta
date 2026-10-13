# E01-S10 to E01-S12 feature handover

## Current state

- E01-S10 RF2 graph builders and vocabulary merging are implemented under
  `plugin_rosetta.vocabulary`.
- Both configured RF2 sources use the shared adapter contract. Physical
  Snapshot and English file selection remains configuration-owned.
- Synthetic tests cover RF2 text handling, 18-digit identifiers, active rows,
  preferred labels, synonyms, is-a edges, cross-source SNOMED identity,
  extension-to-backbone connectivity, Maplib merging, and missing merge inputs.
- Vocabulary provenance now includes explicit per-template optional-value
  omission counts, including zero counts.
- E01-S11 now has a local `plugin_rosetta.artifacts` feature package with
  kind-aware canonical identities, immutable JSON manifests, atomic
  registration, stable listing, dependency impact queries, and typed table,
  SSSOM, and RDF differences.
- The artifact commands are `rosetta artifact register`, `list`, and `diff`;
  they print machine-readable JSON.
- E01-S12 parity is pinned to `sssom-rosetta` revision
  `46fb077c246388f8c692cdcc6b9129a06f669109`.
- The machine-readable retained-workflow inventory is
  `tests/fixtures/parity/workflows.json`; `docs/capability-matrix.md` records
  migrated, changed, and deferred behavior.
- `examples/build_preserved_mapping_set.py` runs offline against tracked
  content and reports eight mappings and eight RDF triples.

## Validation completed

- `uv run tara check` passes with 232 tests and no known dependency vulnerabilities.
- Strict Marimo validation passes.
- The isolated `0.1.0` wheel installs outside the checkout; `rosetta --help`
  and the runnable example complete successfully.
- Wheel inspection confirms the artifact and RF2 modules are present and no
  domain registry resources are packaged.
- A focused release review found six correctness issues. All were fixed:
  dialect-specific RF2 preferred terms, complete RF2 omissions, immutable
  provenance conflicts, concurrent directory races, duplicate diff keys, and
  YAML timestamp canonicalization.
- The follow-up review found and fixed two final catalogue edge cases:
  incompatible table key contracts and YAML date/string identity collisions.

## Remaining work

- Review and commit the staged release candidate.

## Manual release gates

- Compare each vocabulary graph against one licensed real release and record
  only counts and findings.
- Obtain curator approval for documented parity differences.
- Do not stage licensed payloads, extracted releases, generated registry data,
  `.agents/plan/raw_plan_daniel.md`, or `.github/skills/`.
- The developer reviews and commits; the agent does not commit or push.
