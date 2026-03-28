# Contracts

This document defines the exact inter-phase contracts for the adjudication-centered
pipeline.

Current repo support includes two entry modes:

- raw question -> decomposition/collection -> `EvidenceBundle`
- question + imported evidence bundle -> normalize -> `EvidenceBundle`

The contracts below begin once the pipeline has a normalized question and
evidence bundle.

Current runtime note:

- the live runtime now persists Tyler-native Stage 1-6 artifacts in
  `PipelineState`
- Tyler-literal artifacts are the canonical runtime and export contract
- legacy `FinalReport`, legacy downstream handoff, and Stage 1/3 runtime
  projections are gone from the live path
- remaining differences from Tyler's exact intended stack are now shared-infra
  or benchmark/eval concerns, not parallel repo-local runtime contracts

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
raw question or imported bundle
        │
        ▼
Phase 1  Ingest
in:  question text + optional upstream bundle
out: EvidenceBundle + Tyler Stage 1/2 artifacts
        │
        ▼
Phase 2  Analyze
in:  ResearchQuestion + EvidenceBundle + Tyler Stage 1/2
out: Tyler `AnalysisObject[]` + `Stage3AttemptTrace[]`
        │
        ▼
Phase 3  Canonicalize
in:  Tyler `AnalysisObject[]`
out: Tyler `ClaimExtractionResult`
        │
        ▼
Phase 4b Tyler Verification
in:  Tyler Stage 4 artifact + fresh evidence
out: Tyler `VerificationResult`
        │
        ▼
Phase 5 Export
in:  PipelineState
out: Tyler `SynthesisReport` + report.md + summary.md + trace.json + Tyler-native handoff
```

## Cross-Cutting Rules

### Trace Contract

`trace.json` is the serialized `PipelineState`.

Minimum trace expectations:

- original normalized question if available
- imported evidence bundle if available
- Stage 3 attempt traces, including failed runs where possible
- Tyler Stage 4/5/6 artifacts if canonicalization, verification, and export succeeded
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

### Stage 3 Success Contract

A Tyler Stage 3 attempt counts as successful only if:

- it produces a valid Tyler `AnalysisObject`
- the normalized result preserves the assigned `model_alias` and reasoning frame
- the attempt trace records success with a non-negative `claim_count`

Current explicit nuance:

- quality gates now belong on Tyler Stage 3 artifacts and attempt traces, not
  on a second semantic `AnalystRun` runtime contract

### Routing Contract

Dispute routing is code-owned during Tyler Stage 4 normalization.

Current routing:

- empirical + decision-critical -> `stage_5_evidence`
- interpretive + decision-critical -> `stage_5_arbitration`
- preference/spec ambiguity/other + decision-critical -> `stage_6_user_input`
- non-decision-critical disputes -> `logged_only`

The LLM may classify dispute type and criticality.
The route itself is not an LLM judgment.

## Phase -1: Thesis Falsification

This is a validation experiment rather than a pipeline phase.

| Field | Value |
|---|---|
| Input | `question: str` + imported evidence payload |
| Output | 3 analyst artifacts (or equivalent) + minimal claim extraction artifact + manual disagreement review |
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

## Phase 2: Analyze

| Field | Value |
|---|---|
| Input | `ResearchQuestion` + `EvidenceBundle` + Tyler Stage 1/2 |
| Output | Tyler `AnalysisObject[]` + `Stage3AttemptTrace[]` |
| Success | at least 2 successful Tyler analysis objects; different frames assigned; no analyst output contaminates another analyst input |
| Failure | fewer than 2 successful analysts |
| LLM calls | 3 structured calls in parallel |
| Trace | all `stage3_attempts` preserved, including failed ones |

## Phase 3: Canonicalize

| Field | Value |
|---|---|
| Input | Tyler `AnalysisObject[]` + Tyler Stage 1 |
| Output | Tyler `ClaimExtractionResult` |
| Success | claim ledger, assumption set, and dispute queue are structurally coherent and source-grounded |
| Failure | malformed or empty extraction output when Stage 3 clearly produced extractable assertions |
| LLM calls | 1 structured call plus retry only on explicit Stage 4 failure modes |
| Trace | claim count, dispute count, and per-model statistics from Tyler Stage 4 |

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
| Input | one Tyler dispute + its Stage 4 claim entries + relevant evidence context |
| Output | Tyler `VerificationResult` updates + `AdditionalSource[]` |
| Success | arbitration references newly retrieved evidence; claim updates consistent with resolution; dispute status set |
| Failure | verdict without new evidence where new evidence was required; tool errors that prevent search; budget exhaustion before meaningful search |
| Execution mode | agentic — `acall_llm(..., python_tools=[...], max_turns=N)` |
| Code-owned | applying Tyler `ClaimStatusUpdate`s to the Stage 4 ledger; marking disputes resolved; validating new evidence IDs |
| Trace | tool calls made, queries searched, additional sources found, arbitration resolution, cost |

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

This stepping-stone text is now historical only.
The live runtime already executes Tyler-native Stage 5, so older
`ArbitrationResult` / `VerificationQueryBatch` language should be read as
archived implementation history rather than the current contract.

### Historical stepping-stone note

Earlier implementation waves decomposed Phase 4 into query-generation and
single-turn arbitration sub-slices while the agentic path was being proven.
Those sub-slices are now historical only. The live contract is the Tyler-native
Phase 4 contract above: decision-critical disputes in, Tyler
`VerificationResult` plus additional sources out.

## Phase 5: Export

| Field | Value |
|---|---|
| Input | `PipelineState` |
| Output | Tyler `SynthesisReport` + `report.md` + `summary.md` + `trace.json` + Tyler-native handoff |
| Success | claim excerpts resolve in Tyler Stage 5; claim excerpts resolve to source references; unresolved disputes remain visible in `disagreement_map`; gaps remain visible |
| Failure | nonexistent cited claim IDs; source-free cited claims; omitted unresolved disputes |
| LLM calls | 1 synthesis call from structured state |
| Code-owned | grounding validation, trace serialization, handoff serialization |

### Grounding Validation Rules

Before export, code checks:

1. every `claim_id` in `SynthesisReport.claim_ledger_excerpt` resolves in Tyler Stage 5
2. every cited Tyler claim has `source_references`
3. every source reference on a cited Tyler claim resolves in Stage 2 or Stage 5 source inventory
4. unresolved disputes are reflected in `SynthesisReport.disagreement_map`

These are loud export failures, not silent warnings.

## Remaining Open Contract Questions

- whether Tyler-literal should merely beat cached Perplexity or must also match
  the saved dense-dedup anchor before being treated as the uncontested best
  benchmark profile
- which exact quality-first model defaults should be preferred when Tyler's
  ideal frontier stack is unavailable in shared infra
