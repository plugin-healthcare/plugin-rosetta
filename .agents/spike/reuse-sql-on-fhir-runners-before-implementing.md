# Spike: reuse SQL on FHIR runners before implementing

## Question to Answer

Can plugin-rosetta reuse a conformant SQL on FHIR `ViewDefinition` runner from Python without requiring an always-on service, or must it implement a limited Python runner?

## Timebox

The source review is timeboxed to two hours.

The proof of concept is timeboxed to one engineering day.

## Background

The migration plan needs SQL on FHIR projections for nested FHIR resources while keeping the core extensible to non-FHIR formats.

`ViewDefinition` content must remain a versioned artifact, and the execution engine must remain replaceable behind a package protocol.

The default deployment should run locally and lazily where practical without a persistent service.

## Approach

The review used the SQL on FHIR specification, implementation registry, conformance reports, and official implementation repositories or documentation.

The comparison covers runtime boundaries, conformance, nested collections, tabular interoperability, streaming, maintenance, licensing, and deployment.

## Output

This spike provides evidence, an option matrix, a proof-of-concept plan, and a recommendation for ADR-0003, which is not currently in the repository because the draft ADRs were removed.

## Result

### Evidence

- The current SQL on FHIR continuous build is a changing ballot build, so the implementation must pin a published specification or a tested commit.
- The [functional model](https://github.com/HL7/sql-on-fhir/blob/master/input/pagecontent/functional-model.md) defines `column`, `where`, `forEach`, `forEachOrNull`, `select`, and `unionAll` over a constrained FHIRPath subset.
- The [official implementation registry](https://github.com/FHIR/sql-on-fhir.js/blob/main/test_report/public/implementations.json) lists embedded libraries, command-line tools, batch runtimes, and remote services.
- The [shared conformance suite](https://github.com/FHIR/sql-on-fhir.js/tree/main/tests) represents fixtures, ViewDefinitions, and expected rows as JSON.
- The [JavaScript reference implementation](https://github.com/FHIR/sql-on-fhir.js/tree/main/sof-js) uses Bun and provides the reference engine, validator, tests, and a server, but its package documentation exposes tests rather than a stable embedding API.
- [Helios `pysof`](https://github.com/HeliosSoftware/hfs/tree/main/crates/pysof) embeds a Rust runner in Python, supports Python 3.10 through 3.14, accepts Python or serialized JSON input, emits JSON, NDJSON, CSV, or Parquet, and supports chunked NDJSON processing without a service.
- The registered [Helios conformance report](https://heliossoftware.github.io/hfs/test_report.json) currently records 144 passing tests out of 144, but the report is not visibly tied to a tagged `pysof` release and exact shared-suite commit `[NEEDS SOURCE]`.
- [SAS `sqlonfhir`](https://github.com/sassoftware/sqlonfhir) is an Apache-2.0 Python library that uses `fhirpathpy`, accepts resource lists, returns a materialized list of dictionaries, and targets FHIR R4.
- The registered [SAS conformance report](https://raw.githubusercontent.com/sassoftware/sqlonfhir/main/test_report/test_report.json) currently records 110 passing tests out of 118, with the eight boundary-function tests failing.
- [Pathling](https://pathling.csiro.au/docs/libraries/running-queries) embeds its Java and Spark runtime through a Python API, returns a Spark dataframe, supports nested projections, and does not require a persistent service.
- Pathling requires Java 21, and its registered conformance report currently records 131 passing tests out of 133.
- Pathling documents export to Python dataframes and files, but the exact Spark-to-Arrow conversion path and materialization boundary need verification `[NEEDS SOURCE]`.
- [FlatQuack](https://github.com/gotdan/flatquack) compiles ViewDefinitions to DuckDB SQL, runs through Bun or a CLI subprocess, writes CSV or Parquet, and documents larger-than-memory execution through DuckDB.
- FlatQuack is alpha software, its registered report covers 94 passing tests, and its roadmap still lists constants, nested unions, and boundary functions.
- [Google FHIR Data Pipes](https://github.com/google/fhir-data-pipes/tree/master/pipelines) runs as a Java JAR on Apache Beam and writes Parquet without requiring a service, but its deployment weight exceeds the local projection use case.
- Remote products and servers can be adapter options, but making one mandatory would conflict with offline and in-process package use.
- No reviewed embedded runner documents a direct zero-copy Arrow or Polars result interface `[NEEDS SOURCE]`.
- Published long-term support policies for the smaller embedded runners were not found in the reviewed primary sources `[NEEDS SOURCE]`.

### Option matrix

| Option | Boundary and deployment | Conformance and collections | Arrow, Polars, and streaming | Assessment |
| --- | --- | --- | --- | --- |
| Helios `pysof` | In-process Rust extension for Python with optional CLI and server alternatives | Registered 144/144 report and documented nested and collection processing | Chunked NDJSON and Parquet outputs allow adapters, but direct Arrow output is unverified | Best first proof-of-concept candidate |
| SAS `sqlonfhir` | In-process Python library with no service | Registered 110/118 report with boundary-function gaps | Materialized `list[dict]` output and no documented streaming path | Useful control and possible small-data fallback |
| Pathling | Embedded JVM and Spark runtime through Python or CLI | Registered 131/133 report with strong nested projection support | Spark dataframe can remain distributed, but conversion and startup costs need measurement | Strong scale option with a heavy local runtime |
| FlatQuack | Bun CLI or generated DuckDB SQL in a subprocess | Registered 94/94 report against a smaller suite with documented feature gaps | DuckDB supports Parquet and larger-than-memory execution | Promising batch subprocess, not the default embedded path |
| Google FHIR Data Pipes | Java JAR on local or clustered Apache Beam | Registered implementation with batch-oriented ViewDefinition support | Parquet-first batch output | Too heavy for the default library workflow |
| JavaScript reference | Bun runtime, tests, or server | Specification oracle and shared conformance source | No documented stable Python or Arrow embedding contract | Use as an oracle, not the production default |
| Remote service | HTTP adapter to Aidbox, Helios, or another runner | Depends on the selected service and pinned report | Network streaming may be possible | Optional only because it adds operations and availability dependencies |
| New Python runner | Native package code | Conformance burden starts at zero | Could target Arrow and Polars directly | Reject unless reusable runners fail the proof of concept |

### Proof-of-concept plan

1. Pin one SQL on FHIR specification version, one shared conformance-suite commit, and candidate runner versions.
2. Load each `ViewDefinition` from the artifact registry as unchanged versioned JSON content.
3. Adapt `pysof` first and SAS `sqlonfhir` as a Python control behind a private `ProjectionEngine` protocol.
4. Run the selected official cases for `column`, `where`, `select`, `unionAll`, `forEach`, `forEachOrNull`, collection cardinality, resource filtering, resource keys, reference keys, and required FHIRPath functions.
5. Run repository fixtures for nested Patient addresses and collection-valued Observation elements without global dictionary flattening.
6. Convert JSON, NDJSON, or Parquet results into Arrow record batches and Polars lazy frames without exposing runner-specific objects.
7. Measure cold start, throughput, peak memory, chunk behaviour, error fidelity, output types, and offline execution on supported Python 3.14 platforms.
8. Verify the licence, release provenance, wheel availability, maintenance activity, and ability to pin all runtime artifacts.
9. Test the Helios CLI as a subprocess fallback if its Python binding fails packaging or isolation requirements.
10. Record the selected adapter and full conformance report before accepting the ADR.

### Recommendation

Reuse an existing conformant runner behind a private `ProjectionEngine` protocol.

Start the proof of concept with Helios `pysof` because it offers the closest fit to in-process Python, streaming input, current Python support, open tabular outputs, and no required service.

Keep Pathling as the scale-oriented alternative and the Helios CLI as the process-isolated alternative.

Implement a Python runner only if the proof of concept shows that reusable options cannot satisfy deployment, conformance, streaming, and Arrow or Polars integration requirements.

If a Python runner is required, begin only with the selected official cases listed in the proof-of-concept plan and expand by demonstrated FHIR-to-OMOP needs.

### Risks

- Registered conformance totals are not directly comparable unless the report, runner release, specification, and suite revision are pinned together.
- Parquet or NDJSON adaptation may add materialization or copying that defeats the desired lazy boundary.
- Native wheels can narrow supported platforms even when the source package supports the Python version.
- Spark or Bun can complicate installation, startup, observability, and failure handling.
- FHIRPath differences can produce plausible but incorrect rows for collections, precision boundaries, references, and empty values.
- A custom subset can become an accidental dialect unless unsupported ViewDefinitions fail explicitly.
