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
- **Impact**: The tyler_v1_models.py PipelineState matches Tyler exactly. The runtime
  models.py PipelineState is the one actually used by engine.py. They coexist — the
  runtime version is a superset with extra observability fields (stage3_attempts,
  phase_traces, warnings, etc.)
- **Risk**: LOW — the Tyler-shaped PipelineState exists in the schema module, and
  the runtime enriches it with debugging fields. Serialized trace.json uses the
  runtime shape.
- **UNCERTAINTY**: Should the runtime PipelineState be collapsed into the Tyler
  PipelineState, or is the current dual-model approach acceptable? Need Tyler's input.

### 2. Stage 6a interrupt does not check `OTHER` dispute type
- **Tyler spec (V1_SCHEMAS.md line 575-577)**:
  ```python
  interrupt_disputes = [d for d in current_dispute_queue
      if d.type in (DisputeType.PREFERENCE_WEIGHTED, DisputeType.SPEC_AMBIGUITY, DisputeType.OTHER)
      and d.decision_critical == True
      and d.status == DisputeStatus.UNRESOLVED]
  ```
- **Implementation (engine.py:258-262)**:
  ```python
  preference_disputes = [
      d for d in tyler_stage_4_result.dispute_queue
      if d.type.value in {"preference_weighted", "spec_ambiguity"}
      and d.status.value == "unresolved"
  ]
  ```
- **Missing**: `DisputeType.OTHER` is not included in the filter, and
  `decision_critical` is not checked.
- **Impact**: MEDIUM — `other` disputes that are decision-critical would be
  silently skipped instead of surfaced to the user.

### 3. Stage 6a uses Stage 4 dispute queue, not Stage 5's updated queue
- **Tyler spec**: "current_dispute_queue = stage_5_result.updated_dispute_queue
  (if Stage 5 ran) = stage_4_result.dispute_queue (if Stage 5 was skipped)"
- **Implementation (engine.py:260)**: Always reads from
  `tyler_stage_4_result.dispute_queue`, even after Stage 5 has updated statuses.
- **Impact**: MEDIUM — disputes resolved in Stage 5 might still be surfaced to
  the user as if they're unresolved.

### 4. Stage 3 minimum claims is depth-dependent, not fixed at 3
- **Tyler spec (V1_SCHEMAS.md line 233)**: "claims must have at least 3 entries"
- **Implementation**: `min_claims_by_depth: standard: 1, deep: 2, thorough: 3`
- **Impact**: LOW — this means cheap testing runs accept fewer claims than Tyler
  specified. The testing config could be more permissive while keeping the default
  strict per Tyler.
- **UNCERTAINTY**: Tyler said 3 minimum. We relaxed it for depth modes. Is that
  acceptable?

### 5. Hard cap of 4 queries per sub-question not enforced as named constant
- **Tyler spec**: "hard cap: 4 queries per sub-question (named constant)"
- **Implementation**: String template generation produces 4-5 queries per
  sub-question (depending on search_guidance). No explicit cap enforced.
- **Impact**: LOW — we generate ~5 vs Tyler's max 4. Could trivially add a
  `[:4]` slice.

### 6. Exa not used as secondary search provider in collection
- **Tyler spec**: "Tavily (primary, structured JSON) + Exa (secondary,
  semantic/neural)"
- **Implementation**: Tavily is the only provider used by default. Exa is
  wired in `web_search.py` but config.yaml only specifies `search_provider:
  "tavily"`. Tyler envisioned BOTH being used per sub-question.
- **Impact**: MEDIUM — Tyler wanted query diversity via two different search
  paradigms. Currently only keyword search (Tavily) is used.
- **UNCERTAINTY**: Does Tyler want dual-provider search (Tavily + Exa per
  sub-question) or is configurable provider choice acceptable?

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

1. **Dual PipelineState**: Tyler's PipelineState is in tyler_v1_models.py.
   Runtime uses a richer version in models.py with extra observability fields.
   Collapse or keep both?

2. **Stage 3 min claims**: Tyler says 3 minimum. We use depth-dependent
   (1/2/3). Should default be 3 per Tyler, with testing config at 1?

3. **Dual-provider search**: Tyler says Tavily + Exa. We use Tavily only.
   Should we wire both per sub-question, or is configurable choice OK?

4. **Context compaction heuristic**: Tyler says 80K char threshold. We use
   item-count compression. Acceptable substitute?

5. **Stage 6a OTHER dispute type**: Tyler includes it in the interrupt
   filter. We don't. Simple fix — just want to confirm it's intended.
