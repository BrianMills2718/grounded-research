# Tyler Literal Parity Audit

This note answers one narrow question:

> Is the current `grounded-research` runtime implementing Tyler's
> `tyler_response_20260326/` prompts and schemas literally?

Answer: **repo-local live runtime parity is implemented, and repo-local quality
recovery is materially successful, but full Tyler closure is still not
complete**.

**Audit note (2026-04-08):** This document predates the clause-by-clause gap
ledger. It should not be read as overruling `docs/TYLER_SPEC_GAP_LEDGER.md`.
If the ledger identifies a specific local divergence, the ledger is the
canonical source of truth.

The repo-local runtime now runs Tyler-native Stage 1 through Stage 6 contracts
and persists those artifacts in pipeline state. The remaining gap is not stage
contract wiring. It is benchmark quality and explicit shared-infra boundaries.

Full Tyler closure is still not complete because:

- prompt fidelity is now closed repo-locally except for one explicit
  Tyler-internal Stage 2 schema/prompt ambiguity
- provider/model/search assumptions that Tyler specified remain explicit
  shared-infra gaps outside this repo
- frozen comparison coverage is still narrow, and the Tyler-native path still
  trails the saved dense-dedup anchor slightly even after prompt-quality
  recovery

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

Repo-local literal parity is now present in the live runtime for Stage 1
through Stage 6.

Remaining non-literal gaps are now narrower:

1. one explicit Tyler-internal Stage 2 prompt/schema ambiguity remains
   documented locally
2. benchmark-optimal dense-dedup output still differs slightly from the
   Tyler-native path
3. Tyler's provider/model/search assumptions are not wired literally in this
   repo because they belong in shared infrastructure

## Stage-By-Stage Audit

| Surface | Tyler literal contract | Current repo | Literal parity |
|---|---|---|---|
| Shared enums | `EvidenceLabel`, `DisputeType`, `ClaimStatus`, `DisputeStatus`, `ConfidenceLevel`, `ResolutionOutcome` | Tyler schema enums now live in `tyler_v1_models.py` and drive the Tyler-native runtime stages | Yes |
| Stage 1 decomposition | `DecompositionResult` with `SubQuestion.question`, `research_priority`, `search_guidance`, `ResearchPlan`, `StageSummary` | live runtime now produces and persists `PipelineState.tyler_stage_1_result`; current `QuestionDecomposition` is no longer a live runtime contract | Yes (runtime) |
| Stage 2 evidence | `EvidencePackage` made of `SubQuestionEvidence -> Source -> Finding` with `EvidenceLabel` and `quality_score` | live runtime now produces and persists `PipelineState.tyler_stage_2_result`; `EvidenceBundle` remains the mechanical retrieval substrate feeding Stage 2, not a co-equal semantic runtime contract | Yes (runtime) |
| Stage 3 analyst output | `AnalysisObject` with `model_alias`, single `recommendation`, Tyler claim/assumption/counterargument shapes, `stage_summary` | live runtime now produces and persists `PipelineState.tyler_stage_3_results`; runtime trace stores only `stage3_attempts` for observability and no longer stores projected `AnalystRun` | Yes (runtime) |
| Stage 4 claim extraction | single Tyler `ClaimExtractionResult` artifact containing `claim_ledger`, `assumption_set`, `dispute_queue`, and `statistics` | Tyler Stage 4 prompt/schema runs in the live runtime and serializes into `PipelineState.tyler_stage_4_result`; old Stage 4 compatibility protocols are removed from `main` | Yes (runtime) |
| Stage 5 arbitration | `ArbitrationAssessment`, `ClaimStatusUpdate`, `VerificationResult` with post-verification statuses `verified/refuted/unresolved` | Tyler Stage 5 runs in the live runtime and serializes into `PipelineState.tyler_stage_5_result`; old current-shape Stage 5 protocol surfaces are removed from `main` | Yes (runtime) |
| Stage 6 report | Tyler `SynthesisReport` 3-tier schema with `process_summary`, `disagreement_map`, `claim_ledger_excerpt`, `evidence_trail`, etc. | Tyler Stage 6 runs in the live runtime and serializes into `PipelineState.tyler_stage_6_result`; markdown renders directly from Tyler Stage 6 and legacy `FinalReport` export has been removed | Yes (runtime) |
| Prompt package | Tyler literal prompts by stage and frame | Tyler-native prompt surfaces are active for Stages 1-6; repo-local quality recovery improved the tracked UBI case materially, but a small gap to the dense-dedup anchor remains | Runtime-active, locally recovered, not benchmark-identical |

## Current Prompt Inventory vs Tyler Prompt Inventory

| Tyler prompt surface | Current prompt surface | Status |
|---|---|---|
| Stage 1 decomposition | `prompts/tyler_v1_decompose.yaml` | Literal prompt now active in runtime |
| Stage 2 finding extraction | `prompts/tyler_v1_extract_findings.yaml` | Literal prompt now active in runtime |
| Stage 2 query diversification | `prompts/tyler_v1_query_diversification.yaml` | Literal prompt now active in runtime |
| Stage 3 analyst base + 3 frame inserts | `prompts/tyler_v1_analyst.yaml` | Literal prompt now active in runtime |
| Stage 4 claim extraction + dispute localization | `prompts/tyler_v1_stage4.yaml` | Literal prompt/schema active; remaining debt is current-shape model/helper deletion, not Stage 4 prompt wiring |
| Stage 5 verification query generation | `src/grounded_research/verify.py::_build_tyler_verification_queries` | Literal deterministic builder now active; dead prompt file deleted |
| Stage 5 arbitration | `prompts/tyler_v1_arbitration.yaml` | Literal prompt active in runtime |
| Stage 6 synthesis report | `prompts/tyler_v1_synthesis.yaml` | Literal prompt active in runtime and now drives the only live export surface |

## Exact Remaining Non-Literal Gaps That Matter

### 1. Prompt fidelity is now closed repo-locally, with one explicit Tyler ambiguity

The live runtime now uses Tyler-stage prompt files or Tyler-literal
deterministic orchestration for the remaining surfaces:

- Stage 1 decomposition was re-audited and patched
- Stage 2 query diversification was re-audited and confirmed literal
- Stage 2 finding extraction was re-audited and patched
- Stage 5 verification query generation now uses a Tyler-literal deterministic
  builder in `verify.py`

One explicit ambiguity remains:

- Tyler's global shared output block requires a reasoning field on every
  prompt, but Tyler's own Stage 2 `Finding` schema has no reasoning field.
- Local implementation preserves the compatible shared-protocol lines and
  documents the conflict instead of violating Tyler's schema.

### 2. Provider and model assumptions are not literal

Tyler V1 assumes:

- Stage 2 search via Tavily + Exa
- Stage 3 frontier analyst assignment
- Stage 5 Claude Opus arbitration

Current repo intentionally diverged from that for stabilization and shared
infra boundaries. Literal parity would require changing those assumptions or
explicitly deciding to leave provider/model parity out of scope.

### 3. Benchmark quality no longer lags Perplexity, but still differs from the
saved dense-dedup anchor

The benchmark re-anchor wave is complete:

- smoke and tracked fixture runs now serialize Tyler Stage 1-6 artifacts
- the fixture-path Stage 2 emptiness bug was fixed locally
- dense Tyler Stage 2 and Stage 4 both required stronger primary models

Recovery progression:

- `output/tyler_literal_parity_ubi_reanchor_v5/`: regressed badly
- `output/tyler_literal_parity_ubi_reanchor_v7_retry1/`: Stage 3 recovered and
  beat cached Perplexity, but still trailed dense-dedup
- `output/tyler_literal_parity_ubi_reanchor_v8/`: Stage 6 decision packaging
  improved further, still beats cached Perplexity, and remains only slightly
  behind the dense-dedup anchor

So the next local frontier is no longer contract migration. It is:

- finishing literal prompt closure where the repo still diverges
- expanding frozen evaluation beyond one shared case
- keeping the remaining benchmark difference explicit instead of hand-waving it

## Recommendation

Do not claim full Tyler closure yet.

The correct current classification is:

1. repo-local Tyler runtime parity is implemented
2. repo-local Tyler quality recovery is complete enough to beat cached
   Perplexity on the tracked UBI benchmark
3. the remaining gaps are explicit:
   - one explicit Tyler-internal Stage 2 schema/prompt ambiguity remains documented
   - slight divergence from the dense-dedup benchmark-optimal path
   - shared-infra/model-availability differences from Tyler's specified stack

Relevant references:

- `docs/plans/tyler_literal_parity_refactor.md`
- `docs/plans/tyler_literal_parity_benchmark_reanchor.md`
- `docs/plans/tyler_literal_prompt_quality_recovery.md`
- `docs/plans/tyler_faithful_execution_remainder.md`
