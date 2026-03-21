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

These contracts are executor-agnostic.

They define the artifacts that must exist between phases, not one mandatory
orchestration implementation.

The same contract may be satisfied by:

- direct structured calls
- agent loops with tools through `llm_client`
- agent SDK execution through `llm_client`
- a narrow workflow wrapper when explicit pause/resume or approval state is needed

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
| Output | 3 `AnalystRun`-shaped outputs (or equivalent analyst artifacts) + minimal claim extraction artifact + manual disagreement review |
| Success | Disagreements are not mostly framing noise; at least some are decision-relevant |
| Failure | Analysts mostly restate each other; disagreement signal is weak |
| Trace expectation | enough metadata to compare analysts, inspect minimal extracted claims, and record manual review outcome |

Default execution mode:

- start with 3 structured calls
- add one agent SDK comparison run when practical
- do not require a workflow wrapper for this phase

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

## Phase 4: Verification and Arbitration (Agentic)

Phase 4 is the phase most naturally suited to agentic execution. Verification
intrinsically requires tool use: the agent must search for new evidence, read
results, decide if more searching is needed, and then arbitrate based on what
it found. A rigid query→search→arbitrate pipeline cannot adapt its search
strategy based on what it discovers.

Phase 4 uses `llm_client`'s `python_tools` agent loop (`acall_llm` with
`python_tools=[...]`). One agent invocation runs per decision-critical dispute.

| Field | Value |
|---|---|
| Input | one `Dispute` + its `Claim` objects + relevant `EvidenceItem` context |
| Output | `ArbitrationResult` + `list[EvidenceItem]` (newly found) |
| Success | arbitration references newly retrieved evidence; claim updates consistent with verdict; dispute resolution status set |
| Failure | verdict without new evidence where new evidence was required; tool errors that prevent search; budget exhaustion before meaningful search |
| Execution mode | agentic — `acall_llm(..., python_tools=[...], max_turns=N)` |
| Code-owned | applying `ArbitrationResult.claim_updates` to ledger; marking disputes resolved; validating new evidence IDs |
| Trace | tool calls made, queries searched, evidence found, arbitration verdict, cost |

### Agent tools for Phase 4

These are Python callables passed to `llm_client` via `python_tools`:

| Tool | Signature | Purpose |
|---|---|---|
| `search_web` | `(query: str) -> list[dict]` | Search for evidence relevant to the dispute |
| `read_url` | `(url: str) -> str` | Read full content of a search result |
| `record_evidence` | `(content: str, source_url: str, content_type: str) -> str` | Persist new evidence; returns `EvidenceItem.id` |
| `submit_arbitration` | `(verdict: str, reasoning: str, claim_updates: dict, new_evidence_ids: list) -> None` | Finalize the arbitration result |

The agent loop ends when `submit_arbitration` is called or `max_turns` is
reached. If `max_turns` is reached without submission, the dispute is marked
inconclusive with a warning.

### Fallback for Phase -1 and early slices

Before the agentic Phase 4 is wired, verification may use the simpler
sub-slice pattern (Phase 4a: structured query generation + Phase 4b: structured
arbitration). The output contract (`ArbitrationResult` + new evidence) is the
same either way. The agentic version is the target design; the structured
sub-slice is a stepping stone.

### Phase 4 sub-slices (stepping stone)

These remain in the plan as the initial implementation path before the full
agentic loop is wired:

**Phase 4a: Verification Query Generation**

| Field | Value |
|---|---|
| Input | verify-worthy `list[Dispute]` |
| Output | `list[VerificationQueryBatch]` |
| Success | each batch maps to a real dispute; queries specific enough to gather evidence |
| LLM calls | 1 structured call or 1 per dispute |

**Phase 4b: Arbitration and Ledger Update**

| Field | Value |
|---|---|
| Input | `ClaimLedger` + `list[VerificationQueryBatch]` + fresh `EvidenceItem` records |
| Output | updated `ClaimLedger` + `list[ArbitrationResult]` |
| Success | every arbitration references new evidence; claim updates consistent with verdict |
| LLM calls | 1 arbitration call per dispute |
| Code-owned | applying `claim_updates`, dispute resolution flags, warning emission |

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
