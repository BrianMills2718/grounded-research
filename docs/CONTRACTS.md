# Contracts

This document defines the exact inter-phase contracts for the adjudication-first
pipeline.

It is the bridge between:

- [PLAN.md](/home/brian/projects/grounded-research/docs/PLAN.md)
- [DOMAIN_MODEL.md](/home/brian/projects/grounded-research/docs/DOMAIN_MODEL.md)
- [ARCHITECTURE_ONE_PAGE.md](/home/brian/projects/grounded-research/docs/ARCHITECTURE_ONE_PAGE.md)
- `src/grounded_research/models.py`

## Purpose

Each contract answers four questions:

1. What comes in?
2. What goes out?
3. What counts as success?
4. What fails loudly versus warning-and-continue?

## Data Flow Overview

```text
question + upstream bundle
        │
        ▼
Phase 1  Ingest
in:  question text + upstream bundle
out: EvidenceBundle
        │
        ▼
Phase 2a Single Analyst
in:  ResearchQuestion + EvidenceBundle
out: AnalystRun
        │
        ▼
Phase 2b Three Analysts
in:  ResearchQuestion + EvidenceBundle
out: list[AnalystRun]
        │
        ▼
Phase 3a Claim Extraction
in:  list[AnalystRun]
out: list[RawClaim]
        │
        ▼
Phase 3b Deduplication
in:  list[RawClaim]
out: list[Claim]
        │
        ▼
Phase 3c Ledger + Disputes
in:  list[Claim]
out: ClaimLedger
        │
        ▼
Phase 4a Verification Query Generation
in:  list[Dispute]
out: list[VerificationQueryBatch]
        │
        ▼
Phase 4b Arbitration + Ledger Update
in:  ClaimLedger + list[VerificationQueryBatch] + fresh evidence
out: ClaimLedger + list[ArbitrationResult]
        │
        ▼
Phase 5 Export
in:  PipelineState
out: FinalReport + report.md + trace.json + DownstreamHandoff
```

## Cross-Cutting Rules

### Trace Contract

`trace.json` is the serialized `PipelineState`.

Minimum trace expectations:

- original normalized question if available
- imported evidence bundle if available
- analyst runs, including failed runs where possible
- claim ledger if canonicalization succeeded
- final report if export succeeded
- warnings
- per-phase trace entries

Partial traces are valid outputs on failure.

### Budget Contract

Budget values live in `config/config.yaml` once config exists.

Budget exhaustion semantics:

- if the budget cap is advisory for a sub-slice, emit a `PipelineWarning` and
  stop that sub-slice cleanly
- if the cap prevents satisfying a non-negotiable minimum threshold, abort
  loudly with partial trace

Examples:

- fewer than 2 successful analysts: abort
- verification query cap reached: stop generating more queries, warn, continue
- export grounding failure: fail the export stage loudly

### Analyst Success Contract

An `AnalystRun` currently counts as successful if:

- `error is None`

Later tightening may require:

- at least one claim
- at least one recommendation
- evidence references that resolve

The current draft keeps success permissive so the schema layer can be reviewed
before policy is hardened.

### Routing Contract

Dispute routing is code-owned via `DISPUTE_ROUTING` in
`src/grounded_research/models.py`.

Current routing:

- `factual_conflict -> verify`
- `interpretive_conflict -> arbitrate`
- `preference_conflict -> surface`
- `ambiguity -> surface`

The LLM may classify the dispute type.
The route itself is not an LLM judgment.

## Phase -1: Thesis Falsification

This is a validation experiment rather than a pipeline phase.

| Field | Value |
|---|---|
| Input | `question: str` + imported evidence payload |
| Output | 3 analyst text outputs + manual disagreement review |
| Success | Disagreements are not mostly framing noise; at least some are decision-relevant |
| Failure | Analysts mostly restate each other; disagreement signal is weak |
| Trace expectation | enough metadata to compare analysts and record manual review outcome |

## Phase 0: Contracts, Trace, and Review Surface

| Field | Value |
|---|---|
| Input | N/A |
| Output | `docs/DOMAIN_MODEL.md`, `docs/CONTRACTS.md`, `pyproject.toml`, `config/config.yaml`, `prompts/`, draft Pydantic schemas, trace skeleton |
| Success | schema draft is reviewable; trace skeleton serializes; notebook fixtures align with contracts |
| Failure | missing or contradictory schema definitions; notebook becomes the only source of contract truth |

## Phase 1: Ingest

| Field | Value |
|---|---|
| Input | `question: str` + upstream evidence bundle |
| Output | `EvidenceBundle` |
| Success | every `EvidenceItem.source_id` resolves to a `SourceRecord`; provenance and timestamps survive; gaps are explicit |
| Failure | orphan evidence items; malformed bundle; silent dropping of records |
| LLM use | only if semantic normalization is clearly needed |
| Trace | imported_from, source counts, evidence counts, gap summary |

### Upstream Bundle Contract

Current approved upstream sources:

- manual JSON bundle
- `research_v3`
- STORM / `knowledge-storm`
- GPT Researcher

Required normalized outputs regardless of source:

- one `ResearchQuestion`
- zero or more `SourceRecord`
- zero or more `EvidenceItem`
- explicit `gaps`
- `imported_from`

### `research_v3` Mapping Status

Current mapping assumptions are partially verified against local
`research_v3/models.py` and sample `graph.yaml` outputs.

Verified high-level surfaces:

- `InvestigationGoal.original_query`
- `Source`
- `Source.credibility`
- `Source.api_record_id`
- persisted `graph.yaml`

Exact adapter field mapping should remain provisional until a real ingest slice
is wired and tested against a committed sample.

## Phase 2a: Single Analyst

| Field | Value |
|---|---|
| Input | `ResearchQuestion` + `EvidenceBundle` |
| Output | `AnalystRun` |
| Success | parses to valid `AnalystRun`; claims reference real evidence IDs; at least one claim and one recommendation are expected in live mode |
| Failure | malformed structured output; invalid evidence references; empty critical sections in live mode |
| LLM calls | 1 structured call |
| Trace | assigned frame, model, success/failure, summary |

## Phase 2b: Three Independent Analysts

| Field | Value |
|---|---|
| Input | `ResearchQuestion` + `EvidenceBundle` |
| Output | `list[AnalystRun]` |
| Success | at least 2 successful analysts; different frames assigned; no analyst output contaminates another analyst input |
| Failure | fewer than 2 successful analysts |
| LLM calls | 3 structured calls in parallel |
| Trace | all analyst traces preserved, including failed ones |

## Phase 3a: Claim Extraction

| Field | Value |
|---|---|
| Input | `list[AnalystRun]` |
| Output | `list[RawClaim]` |
| Success | every `RawClaim` traces to an `AnalystRun`; no provenance loss |
| Failure | invented claims or loss of analyst provenance |
| LLM calls | ideally 0 in the first slice, since `AnalystRun.claims` already exist |
| Trace | raw claim count by analyst |

## Phase 3b: Deduplication

| Field | Value |
|---|---|
| Input | `list[RawClaim]` |
| Output | `list[Claim]` |
| Success | source raw claim IDs preserved; analyst sources preserved; near-identical claims merge conservatively |
| Failure | over-merge, under-merge, or lost provenance |
| LLM calls | 1 structured call |
| Trace | raw-claim count, canonical-claim count, merge summary |

Failure semantics:

- malformed dedup output is a loud failure for the sub-slice
- do not silently substitute heuristic dedup logic

## Phase 3c: Ledger Assembly and Dispute Detection

| Field | Value |
|---|---|
| Input | `list[Claim]` |
| Output | `ClaimLedger` |
| Success | disputes reference real claim IDs; routes match `DISPUTE_ROUTING`; no phantom disputes survive review |
| Failure | invalid claim references; routes that disagree with the code-owned table |
| LLM calls | 1 structured dispute-classification call |
| Code-owned | ID assignment, routing, ledger assembly |
| Trace | dispute count by type and route |

## Phase 4a: Verification Query Generation

| Field | Value |
|---|---|
| Input | verify-worthy `list[Dispute]` |
| Output | `list[VerificationQueryBatch]` |
| Success | each batch maps to a real dispute; queries are specific enough to gather clarifying evidence |
| Failure | batches reference nonexistent disputes; empty query lists |
| LLM calls | 1 structured call or 1 per dispute |
| Trace | query batches, dispute coverage, warning if budget truncates coverage |

## Phase 4b: Arbitration and Ledger Update

| Field | Value |
|---|---|
| Input | `ClaimLedger` + `list[VerificationQueryBatch]` + fresh `EvidenceItem` records |
| Output | updated `ClaimLedger` + `list[ArbitrationResult]` |
| Success | every arbitration references new evidence; claim updates are consistent with verdict; resolved disputes are marked resolved |
| Failure | verdict without new evidence where new evidence was required; invalid claim updates; contradiction between result and ledger state |
| LLM calls | 1 arbitration call per dispute |
| Code-owned | application of `claim_updates`, dispute resolution flags, warning emission |
| Trace | arbitration verdicts, new evidence counts, updated claim statuses |

## Phase 5: Export

| Field | Value |
|---|---|
| Input | `PipelineState` |
| Output | `FinalReport` + `report.md` + `trace.json` + `DownstreamHandoff` |
| Success | cited claim IDs resolve; cited claims resolve to evidence; unresolved disputes remain visible; gaps remain visible |
| Failure | nonexistent cited claim IDs; evidence-free cited claims; omitted unresolved disputes |
| LLM calls | 1 synthesis call from structured state |
| Code-owned | grounding validation, trace serialization, handoff serialization |

### Grounding Validation Rules

Before export, code checks:

1. every `claim_id` in `FinalReport.cited_claim_ids` resolves in `ClaimLedger`
2. every cited claim has `evidence_ids`
3. every `evidence_id` on a cited claim resolves in `EvidenceBundle`
4. unresolved disputes are reflected in the report

These are loud export failures, not silent warnings.

## Remaining Open Contract Questions

- whether analyst success should be tightened now or after the first live slice
- whether `DownstreamHandoff` should carry a flattened evidence index in addition
  to the raw bundle data
- whether verification query generation should be one batch call or one call per
  dispute in the first live implementation
