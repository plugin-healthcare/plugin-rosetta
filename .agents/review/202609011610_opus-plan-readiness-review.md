# Opus plan readiness review

> **Status:** Superseded by the simplified build-first plan.

This review assessed the broader multi-package plan and should not be used to create issues for the current scope.

## Verdict

**Ready with minor edits.**

The scope boundary is coherent and the plan can become issues after the findings below are resolved.

## Findings

1. ADR-0001 must define artifact identity, publisher-assigned versions, and ordering semantics.
2. ADR-0001 must define alias concurrency, registry metadata migration, and garbage collection ownership.
3. Nyctea needs a proposed dependency ADR before it becomes part of the core validation path.
4. Registry lifecycle `candidate` should be renamed to avoid collision with mapping candidates.
5. Registry/storage and graph/terminology milestones must be split into smaller stories with one minimal adapter closing each milestone.
6. RDF triple diff should move after RDF support or explicitly use a plain RDF parser.
7. The portable bundle needs a published JSON Schema and a consumer test that does not import Rosetta.
8. `ProjectionEngine` belongs to the FHIR module rather than the mapping-agnostic core.
9. Maplib remains a core dependency, while its benchmark establishes performance and memory baselines and identifies operations that need optimization.
10. `rosetta run` should be marked as a reserved namespace outside this plan.
11. Small conformance examples need a strict synthetic-data boundary.
12. Application services need an owning milestone and the CLI must remain a thin adapter.
13. OMOP-to-FHIR needs an explicit trigger and should remain deferred rather than appearing as a scheduled milestone.

## ADR status

| ADR | Recommendation |
| --- | --- |
| ADR-0001 | Keep Proposed until version ordering and concurrent promotion are decided |
| ADR-0002 | Keep Proposed until its rationale is reviewed; the benchmark does not gate Maplib adoption |
| ADR-0003 | Keep Proposed until the SQL on FHIR proof of concept selects a runner |
| ADR-0004 | Accept after clarifying that `rosetta run` is reserved and out of scope |

## Suggested epics

1. Mapping-agnostic core contracts.
2. Generic validation and mapping authoring.
3. Artifact registry and storage.
4. Graph, ontology, and terminology adapters.
5. FHIR and OMOP artifact support.
6. Initial FHIR-to-OMOP bundles.
7. Mapping generation and evaluation.
8. Hardening and release.

## Deferred

- OMOP-to-FHIR artifacts.
- `plugin-rosetta-runtime` extraction.
- `plugin-rosetta-ui`.
