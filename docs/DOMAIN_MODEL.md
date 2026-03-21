# Domain Model

This document defines the field-level domain model for `grounded-research`.

It is the human-readable companion to the draft Pydantic models in
`src/grounded_research/models.py`.

Use this file to review:

- what objects exist
- what fields each object carries
- how objects relate to each other
- which objects are current v1 entities versus planned-future entities

## Design Intent

The project is adjudication-first.

That means the domain model is centered on:

- imported evidence
- independent analyst runs
- canonical claims
- typed disputes
- arbitration results
- final grounded export

It is not centered on a planner-first or retrieval-first pipeline.

## ID Conventions

Current draft prefixes:

- `S-` source records
- `E-` evidence items
- `A-` assumptions
- `AN-` analyst runs
- `RC-` raw claims
- `C-` canonical claims
- `D-` disputes
- `AR-` arbitration results

These IDs are trace-facing and human-readable. They are not meant to be stable
content hashes in v1.

## Literal Types

Current draft literals in `models.py`:

- `TimeSensitivity`: `stable | mixed | time_sensitive`
- `SourceType`: `government_db | court_record | news | academic | primary_document | web_search | social_media | platform_transparency | other`
- `QualityTier`: `authoritative | reliable | secondary | unknown`
- `ClaimStatus`: `initial | supported | revised | refuted | inconclusive`
- `DisputeType`: `factual_conflict | interpretive_conflict | preference_conflict | ambiguity`
- `DisputeRoute`: `verify | arbitrate | surface`
- `ArbitrationVerdict`: `supported | revised | refuted | inconclusive`
- `AnalystFrame`: `verification_first | structured_decomposition | step_back_abstraction | general`
- `PipelinePhase`: `init | ingest | analyze | canonicalize | adjudicate | export | complete | failed`

## Current v1 Entities

### ResearchQuestion

Purpose:

- normalized question object carried through all phases

Fields:

- `text: str`
- `time_sensitivity: TimeSensitivity`
- `scope_notes: str`
- `key_entities: list[str]`

Notes:

- `time_sensitivity` lives here in the current draft.
- This is the right place for scope bounding and entity hints.

### SourceRecord

Purpose:

- one imported or retrieved source document / API record

Fields:

- `id: str`
- `url: str`
- `title: str`
- `source_type: SourceType`
- `quality_tier: QualityTier`
- `published_at: datetime | None`
- `retrieved_at: datetime`
- `recency_score: float`
- `api_record_id: str | None`
- `upstream_source_id: str | None`

Notes:

- This is where recent-first evidence policy becomes concrete.
- `upstream_source_id` preserves provenance back to imported systems.

### EvidenceItem

Purpose:

- one discrete piece of evidence extracted from a source

Fields:

- `id: str`
- `source_id: str`
- `content: str`
- `content_type: text | data_point | quotation | summary`
- `relevance_note: str`
- `extraction_method: manual | llm | upstream`

Relationship:

- many `EvidenceItem` records may point to one `SourceRecord`

### EvidenceBundle

Purpose:

- phase boundary object between ingest and analysis

Fields:

- `question: ResearchQuestion`
- `sources: list[SourceRecord]`
- `evidence: list[EvidenceItem]`
- `gaps: list[str]`
- `imported_from: str | None`
- `imported_at: datetime`

Notes:

- This is the canonical ingest output.
- It is intentionally richer than just `list[EvidenceItem]`.

### Assumption

Purpose:

- first-class assumption surfaced by an analyst

Fields:

- `id: str`
- `statement: str`
- `basis: str`
- `challenged: bool`

Notes:

- Assumptions are first-class now.
- A full `AssumptionLedger` is still deferred.

### RawClaim

Purpose:

- one analyst-scoped claim before canonicalization

Fields:

- `id: str`
- `statement: str`
- `evidence_ids: list[str]`
- `confidence: high | medium | low`
- `reasoning: str`

Notes:

- This is the output shape analysts produce directly.
- `RawClaim` is pre-dedup and pre-ledger.

### Recommendation

Purpose:

- prescriptive conclusion from one analyst

Fields:

- `statement: str`
- `supporting_claim_ids: list[str]`
- `conditions: str`

### Counterargument

Purpose:

- strongest objection an analyst raises

Fields:

- `target: str`
- `argument: str`
- `evidence_ids: list[str]`

### AnalystRun

Purpose:

- one independent structured analyst output

Fields:

- `id: str`
- `analyst_label: str`
- `frame: AnalystFrame`
- `model: str`
- `claims: list[RawClaim]`
- `assumptions: list[Assumption]`
- `recommendations: list[Recommendation]`
- `counterarguments: list[Counterargument]`
- `summary: str`
- `completed_at: datetime`
- `error: str | None`

Computed property:

- `succeeded: bool`

Success rule:

- current draft defines success as `error is None`
- later tightening may also require minimum non-empty structured fields

### Claim

Purpose:

- canonical claim in the ledger after deduplication

Fields:

- `id: str`
- `statement: str`
- `status: ClaimStatus`
- `source_raw_claim_ids: list[str]`
- `analyst_sources: list[str]`
- `evidence_ids: list[str]`
- `confidence: high | medium | low`
- `status_reason: str`

Lifecycle:

- starts as `initial`
- may become `supported | revised | refuted | inconclusive`

### Dispute

Purpose:

- typed conflict between canonical claims

Fields:

- `id: str`
- `dispute_type: DisputeType`
- `route: DisputeRoute`
- `claim_ids: list[str]`
- `description: str`
- `severity: decision_critical | notable | minor`
- `resolved: bool`
- `resolution_summary: str`

Notes:

- `route` is code-owned from `DISPUTE_ROUTING`
- `claim_ids` must all resolve to canonical `Claim.id`

### VerificationQueryBatch

Purpose:

- explicit phase boundary object between dispute selection and arbitration search

Fields:

- `dispute_id: str`
- `queries: list[str]`
- `rationale: str`

### ArbitrationResult

Purpose:

- outcome of verifying and adjudicating one dispute

Fields:

- `id: str`
- `dispute_id: str`
- `verdict: ArbitrationVerdict`
- `new_evidence_ids: list[str]`
- `reasoning: str`
- `claim_updates: dict[str, ClaimStatus]`
- `completed_at: datetime`

Notes:

- This object is the only thing allowed to change claim statuses during adjudication.

### ClaimLedger

Purpose:

- canonical product artifact of the project

Fields:

- `claims: list[Claim]`
- `disputes: list[Dispute]`
- `arbitration_results: list[ArbitrationResult]`

Convenience lookups:

- `claim_by_id`
- `disputes_for_claim`
- `unresolved_disputes`
- `decision_critical_disputes`

### FinalReport

Purpose:

- grounded user-facing rendering of pipeline state

Fields:

- `title: str`
- `question: str`
- `recommendation: str`
- `alternatives: list[str]`
- `disagreement_summary: str`
- `evidence_gaps: list[str]`
- `flip_conditions: list[str]`
- `cited_claim_ids: list[str]`
- `generated_at: datetime`

Notes:

- An explicit assumptions section is still deferred but retained in the plan.

### DownstreamHandoff

Purpose:

- structured export for downstream systems such as `onto-canon`

Fields:

- `downstream_target: str`
- `question: ResearchQuestion`
- `claim_ledger: ClaimLedger`
- `sources: list[SourceRecord]`
- `evidence: list[EvidenceItem]`
- `generated_at: datetime`

### PipelineWarning

Purpose:

- non-fatal warning persisted to trace

Fields:

- `phase: PipelinePhase`
- `code: str`
- `message: str`
- `timestamp: datetime`
- `context: dict[str, Any]`

### PhaseTrace

Purpose:

- per-phase observability record inside the trace artifact

Fields:

- `phase: PipelinePhase`
- `started_at: datetime`
- `completed_at: datetime | None`
- `succeeded: bool`
- `error: str | None`
- `llm_calls: int`
- `llm_cost_usd: float`
- `output_summary: str`

### PipelineState

Purpose:

- top-level trace artifact for successful or failed runs

Fields:

- `run_id: str`
- `started_at: datetime`
- `completed_at: datetime | None`
- `current_phase: PipelinePhase`
- `success: bool`
- `question: ResearchQuestion | None`
- `evidence_bundle: EvidenceBundle | None`
- `analyst_runs: list[AnalystRun]`
- `claim_ledger: ClaimLedger | None`
- `report: FinalReport | None`
- `phase_traces: list[PhaseTrace]`
- `warnings: list[PipelineWarning]`

Helper:

- `add_warning(...)`

## Planned-Future Entities

These remain part of the plan but are not current v1 schema requirements:

### AssumptionLedger

Purpose:

- canonicalized, deduplicated assumption registry across analysts and phases

Reason deferred:

- assumptions are already first-class objects
- a full cross-analyst assumption-ledger can follow the core claim-ledger slice

## Relationship Summary

- one `ResearchQuestion` feeds one `EvidenceBundle`
- one `EvidenceBundle` contains many `SourceRecord` and many `EvidenceItem`
- three or more `AnalystRun` objects consume the same `EvidenceBundle`
- one `AnalystRun` contains many `RawClaim`, `Assumption`, `Recommendation`, and `Counterargument`
- many `RawClaim` objects are deduplicated into many `Claim` objects
- many `Claim` objects may participate in many `Dispute` objects
- many `ArbitrationResult` objects update one `ClaimLedger`
- one `PipelineState` contains the trace of the full run

## Current Gaps

These are the remaining design questions after the current draft:

- whether `AnalystRun.succeeded` should require non-empty claims in addition to `error is None`
- whether verification queries should stay as a lightweight object or grow richer metadata
- whether `FinalReport` should split into multiple typed sections or stay compact in v1
- when `AssumptionLedger` should be promoted from deferred to current
