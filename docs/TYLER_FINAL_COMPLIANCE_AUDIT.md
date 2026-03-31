# Tyler V1 Final Compliance Audit

Date: 2026-03-31
Audited against: `2026_0325_tyler_feedback/` (Build Plan, Design, Schemas, Prompts)

## Methodology

Line-by-line comparison of Tyler's V1_SCHEMAS.md against
`src/grounded_research/tyler_v1_models.py`, and Tyler's Build Plan
against `engine.py`, `collect.py`, `verify.py`, `analysts.py`,
`canonicalize.py`, `export.py`, and all prompt files.

## CONFIRMED: Tyler-Literal

These items match Tyler's spec exactly:

### Enums (all 7)
- EvidenceLabel: 4 values + weights (1.0/0.8/0.5/0.3) ✅
- DisputeType: 5 values ✅
- ClaimStatus: 8 values ✅
- DisputeStatus: 4 values ✅
- ConfidenceLevel: 3 values ✅
- ResolutionOutcome: 4 values ✅
- ChangeBasicType: 3 values (our addition, not in Tyler schema) ✅

### Stage 1 schemas
- StageSummary: all 6 fields match ✅
- SubQuestion: all 5 fields match ✅
- ResearchPlan: all 3 fields match ✅
- DecompositionResult: all 5 fields match, min_length=2/max_length=6 ✅

### Stage 2 schemas
- Finding: all 3 fields match ✅
- Source: 7 fields, Tyler has 6 (we add `publication_date`) — additive, no conflict ✅
- SubQuestionEvidence: all 4 fields match ✅
- EvidencePackage: all 4 fields match ✅

### Stage 3 schemas
- Claim: all 5 fields match ✅
- Assumption: all 4 fields match ✅
- CounterArgument: all 3 fields match ✅
- AnalysisObject: all 10 fields match ✅

### Stage 4 schemas
- ClaimLedgerEntry: Tyler's 9 fields + our 2 additive (status_at_extraction, is_provisional) ✅
- AssumptionSetEntry: all 6 fields match ✅
- ModelPosition: all 2 fields match ✅
- DisputeQueueEntry: all 9 fields match ✅
- ExtractionStatistics: all 6 fields match ✅
- ClaimExtractionResult: all 5 fields match ✅

### Stage 5 schemas
- ClaimStatusUpdate: Tyler's 4 fields + our 1 additive (basis_for_change) ✅
- ArbitrationAssessment: all 5 fields match ✅
- AdditionalSource: all 6 fields match ✅
- VerificationResult: all 7 fields match (including rounds_used) ✅

### Stage 6 schemas
- Tradeoff, DisagreementMapEntry (with chosen_interpretation), PreservedAlternative,
  KeyAssumption, ConfidenceAssessment, ClaimLedgerExcerpt, EvidenceTrailEntry: all match ✅
- SynthesisReport: all 13 fields (11 components + reasoning + stage_summary) match ✅

### PipelineState schema (in tyler_v1_models.py)
- PipelineState: all 16 fields match Tyler exactly ✅
- PipelineError: all 5 fields match ✅

### Pipeline behavior
- Source quality scoring: deterministic URL lookup table ✅
- Query generation: string templates, not LLM call ✅
- Evidence label weights: wired in prompts and code ✅
- Verification budget: max 3 queries/dispute, max 2 rounds ✅
- Counterfactual patterns: [topic] limitations, [claim] contradicted by ✅
- Anonymization: A/B/C labeling + identity scrubbing ✅
- Anti-conformity: stated in all relevant prompts ✅
- Context rot: original query at start/end of prompts ✅
- Partial trace on abort ✅
- Fallback chains on must-succeed stages ✅
- Stage 5 skip condition (deterministic) ✅
- Reasoning field on all model outputs ✅

## DEVIATIONS: Things that differ from Tyler's literal spec

### 1. Runtime PipelineState uses `tyler_` prefix on field names
- **Tyler spec**: `stage_1_result`, `stage_2_result`, `stage_3_results`, etc.
- **Implementation**: `tyler_stage_1_result`, `tyler_stage_2_result`, `tyler_stage_3_results`
- **Location**: `src/grounded_research/models.py:345-356`
- **Impact**: LOW — the Tyler-shaped PipelineState exists in tyler_v1_models.py
  and matches exactly. The runtime models.py PipelineState is a superset with
  extra observability fields (stage3_attempts, phase_traces, warnings).
- **UNCERTAINTY**: Should the runtime PipelineState be collapsed into the Tyler
  PipelineState, or is the current dual-model approach acceptable? Need Tyler's input.

### ~~2. Stage 6a interrupt does not check `OTHER` dispute type~~ — FIXED
Fixed in commit 3805186 (2026-03-31). Stage 6a now includes `other` type,
checks `decision_critical`, and reads the post-Stage-5 updated queue.

### ~~3. Stage 6a uses Stage 4 dispute queue, not Stage 5's updated queue~~ — FIXED
Fixed in commit 3805186 (2026-03-31). Now reads `stage_5_result.updated_dispute_queue`
when Stage 5 ran, falls back to Stage 4 queue otherwise.

### ~~4. Stage 3 minimum claims is depth-dependent, not fixed at 3~~ — FIXED
Fixed in commit 3805186 (2026-03-31). Default config now sets min_claims=3
for all depths per Tyler spec. Testing config keeps relaxed 1/2/3.

### ~~5. Hard cap of 4 queries per sub-question not enforced~~ — FIXED
Fixed in commit 3805186 (2026-03-31). Named constant
`_MAX_QUERIES_PER_SUB_QUESTION = 4` caps generation in collect.py.

### ~~6. Exa not used as secondary search provider~~ — FIXED
Fixed in commit 82a0380 (2026-03-31). Exa now runs as secondary search
alongside Tavily for every query. Graceful no-op if EXA_API_KEY not set.

### 7. Context compaction threshold not implemented
- **Tyler spec**: "Compress prior-stage artifacts when input exceeds ~80K
  characters (~20K tokens)"
- **Implementation**: Evidence compression exists (compress.py) but operates
  on item count, not character count. No explicit 80K char compaction step
  before synthesis.
- **Impact**: LOW — the pipeline does compress evidence, just using a different
  heuristic (item count threshold vs character count threshold).
- **UNCERTAINTY**: Is item-count compression an acceptable substitute for
  Tyler's char-count heuristic?

## ADDITIVE FIELDS (not in Tyler spec, added by us)

These are backward-compatible additions with defaults. Tyler didn't ask for
them but they don't conflict:

1. `Source.publication_date` (Optional, default None)
2. `ClaimLedgerEntry.status_at_extraction` (Optional, default None) — constraint #4
3. `ClaimLedgerEntry.is_provisional` (bool, default True) — constraint #8
4. `ClaimStatusUpdate.basis_for_change` (enum, default new_evidence) — constraint #9

## ITEMS FOR TYLER'S INPUT

Only 2 open questions remain (items 2-5 were fixed 2026-03-31):

1. **Dual PipelineState**: Tyler's PipelineState is in tyler_v1_models.py.
   Runtime uses a richer version in models.py with extra observability fields
   (stage3_attempts, phase_traces, warnings). Collapse or keep both?

2. **Context compaction heuristic**: Tyler says 80K char threshold. We use
   item-count compression (threshold: 80 items). Acceptable substitute?
