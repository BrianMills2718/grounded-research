# Tyler Literal Parity Audit

This note answers one narrow question:

> Is the current `grounded-research` runtime implementing Tyler's
> `tyler_response_20260326/` prompts and schemas literally?

Answer: **no**.

The repo implements many Tyler V1 ideas in adapted form, but it does not
currently run Tyler's exact prompt text or exact schema contracts end-to-end.

## Scope

Compared artifacts:

- `tyler_response_20260326/3. V1_SCHEMAS (1).md`
- `tyler_response_20260326/4. V1_PROMPTS (1).md`
- current runtime contracts in `src/grounded_research/models.py`
- current prompt package in `prompts/`
- current orchestration in `engine.py`, `analysts.py`, `canonicalize.py`,
  `verify.py`, and `export.py`

This audit is about **literal parity**, not about whether the current repo is
good, benchmarked, or methodologically similar.

## Executive Verdict

Literal parity is absent for four independent reasons:

1. current enums and stage-output models are not Tyler's exact schema surface
2. current prompt files are aligned to Tyler's method but are not Tyler's exact
   prompt text
3. Stage 4 and Stage 6 are architecturally different from Tyler's literal
   artifact design
4. Tyler's provider/model assumptions are not wired literally in this repo

## Stage-By-Stage Audit

| Surface | Tyler literal contract | Current repo | Literal parity |
|---|---|---|---|
| Shared enums | `EvidenceLabel`, `DisputeType`, `ClaimStatus`, `DisputeStatus`, `ConfidenceLevel`, `ResolutionOutcome` | repo-local `Literal[...]` unions with different values | No |
| Stage 1 decomposition | `DecompositionResult` with `SubQuestion.question`, `research_priority`, `search_guidance`, `ResearchPlan`, `StageSummary` | `QuestionDecomposition` with typed `SubQuestion.text`, `falsification_target`, `optimization_axes`, free-text `research_plan`, optional `ambiguous_terms` | No |
| Stage 2 evidence | `EvidencePackage` made of `SubQuestionEvidence -> Source -> Finding` with `EvidenceLabel` and `quality_score` | `EvidenceBundle` made of `SourceRecord` and `EvidenceItem` with `quality_tier`, `recency_score`, and content extracts | No |
| Stage 3 analyst output | `AnalysisObject` with `model_alias`, single `recommendation`, Tyler claim/assumption/counterargument shapes, `stage_summary` | `AnalystRun` with `analyst_label`, `model`, `frame`, lists of `Recommendation`, `RawClaim`, `Assumption`, `Counterargument`, no Tyler `StageSummary` field | No |
| Stage 4 claim extraction | single Tyler `ClaimExtractionResult` artifact containing `claim_ledger`, `assumption_set`, `dispute_queue`, and `statistics` | split across `claimify`, `dedup`, `dispute_classify`, then assembled into repo-local `ClaimLedger` + `Dispute` + `ArbitrationResult` surfaces | No |
| Stage 5 arbitration | `ArbitrationAssessment`, `ClaimStatusUpdate`, `VerificationResult` with post-verification statuses `verified/refuted/unresolved` | repo-local `ArbitrationResult`, `ClaimUpdate`, `ClaimStatus` values `supported/revised/refuted/inconclusive` | No |
| Stage 6 report | Tyler `SynthesisReport` 3-tier schema with `process_summary`, `disagreement_map`, `claim_ledger_excerpt`, `evidence_trail`, etc. | repo-local `FinalReport` plus separate markdown long report rendering | No |
| Prompt package | Tyler literal prompts by stage and frame | current prompt texts are adapted and expanded for current contracts | No |

## Current Prompt Inventory vs Tyler Prompt Inventory

| Tyler prompt surface | Current prompt surface | Status |
|---|---|---|
| Stage 1 decomposition | `prompts/decompose.yaml` | Adapted, not literal |
| Stage 2 finding extraction | `prompts/extract_evidence.yaml` | Adapted, not literal |
| Stage 2 query diversification | `prompts/query_generation.yaml` | Adapted, not literal |
| Stage 3 analyst base + 3 frame inserts | `prompts/analyst.yaml` with inline frame branches | Adapted, not literal |
| Stage 4 claim extraction + dispute localization | split across `prompts/claimify.yaml`, `prompts/dedup.yaml`, `prompts/dispute_classify.yaml` | Architecturally divergent |
| Stage 5 verification query generation | `prompts/verification_queries.yaml` | Adapted, not literal |
| Stage 5 arbitration | `prompts/arbitration.yaml` | Adapted, not literal |
| Stage 6 synthesis report | `prompts/synthesis.yaml` + `prompts/long_report.yaml` | Architecturally divergent |

## Exact Non-Literal Gaps That Matter

### 1. Enum and lifecycle mismatch

Tyler's literal contract expects:

- `DisputeType`: `empirical`, `interpretive`, `preference_weighted`,
  `spec_ambiguity`, `other`
- `ClaimStatus`: `initial`, `supported`, `contested`, `contradicted`,
  `insufficient_evidence`, `verified`, `refuted`, `unresolved`
- `DisputeStatus`: `unresolved`, `resolved`, `deferred_to_user`, `logged_only`

Current repo uses a different surface:

- `DisputeType`: `factual_conflict`, `interpretive_conflict`,
  `preference_conflict`, `ambiguity`
- `ClaimStatus`: `initial`, `supported`, `revised`, `refuted`,
  `inconclusive`
- no Tyler `DisputeStatus` enum

This is not cosmetic. It changes routing, report semantics, and post-stage
validation.

### 2. Stage 4 is not Tyler's artifact

Tyler's Stage 4 contract expects one canonical `ClaimExtractionResult`
containing:

- `ClaimLedgerEntry`
- `AssumptionSetEntry`
- `DisputeQueueEntry`
- `ExtractionStatistics`

Current runtime does not have that stage artifact. It splits the work across
multiple prompts and stores the result in repo-local models. Literal prompt
porting is impossible without first changing the Stage 4 contract.

### 3. Stage 6 is not Tyler's artifact

Tyler's final model output is a structured `SynthesisReport`.

Current runtime does:

1. structured `FinalReport` for grounding checks
2. separate long-form markdown synthesis

That means Tyler's literal synthesis prompt cannot be adopted safely without
replacing the final-stage contract and the report validator.

### 4. Tyler prompt text is not current prompt text

Current prompts preserve major Tyler ideas:

- anti-conformity
- counterargument requirement
- claim specificity
- disagreement emphasis

But the texts are not literal. This matters because the user asked for literal
implementation, not methodological similarity.

### 5. Provider and model assumptions are not literal

Tyler V1 assumes:

- Stage 2 search via Tavily + Exa
- Stage 3 frontier analyst assignment
- Stage 5 Claude Opus arbitration

Current repo intentionally diverged from that for stabilization and shared
infra boundaries. Literal parity would require changing those assumptions or
explicitly deciding to leave provider/model parity out of scope.

## What A Literal Refactor Actually Means

Achieving literal parity is a major refactor.

It would require:

1. introducing Tyler-native schema classes in code
2. migrating stage outputs to those classes
3. porting Tyler prompt text literally, stage by stage
4. rewriting Stage 4 and Stage 6 orchestration around Tyler's artifact shapes
5. updating validators, tests, and benchmark harnesses to the new contracts
6. deciding whether Tyler provider/model assumptions are literal requirements
   or external shared-infra dependencies

## Recommendation

Do not claim literal parity today.

If the user wants literal Tyler implementation, the correct next move is a
dedicated migration plan with phased acceptance gates:

1. exact Tyler schema contract lands in code
2. Stage 1-3 migrate to Tyler contracts
3. Stage 4 migrates as the major contract refactor
4. Stage 5-6 migrate
5. benchmark and regression harnesses are re-anchored

That plan is captured in `docs/plans/tyler_literal_parity_refactor.md`.
