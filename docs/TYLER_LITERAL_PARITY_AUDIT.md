# Tyler Literal Parity Audit

This note answers one narrow question:

> Is the current `grounded-research` runtime implementing Tyler's
> `tyler_response_20260326/` prompts and schemas literally?

Answer: **repo-local runtime parity is implemented, but quality parity is not
yet proven**.

The repo-local runtime now runs Tyler-native Stage 1 through Stage 6 contracts
and persists those artifacts in pipeline state. The remaining gap is not stage
contract wiring. It is benchmark quality and explicit shared-infra boundaries.

Full Tyler closure is still not complete because:

- current compatibility projections still exist for downstream surfaces
- provider/model/search assumptions that Tyler specified remain explicit
  shared-infra gaps outside this repo
- the Tyler-native path still trails the saved dense-dedup anchor slightly even
  after prompt-quality recovery

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

1. current compatibility projections still coexist with the Tyler-native
   runtime artifacts
2. tracked benchmark re-anchor closed with regressed usefulness
3. Tyler's provider/model/search assumptions are not wired literally in this
   repo because they belong in shared infrastructure

## Stage-By-Stage Audit

| Surface | Tyler literal contract | Current repo | Literal parity |
|---|---|---|---|
| Shared enums | `EvidenceLabel`, `DisputeType`, `ClaimStatus`, `DisputeStatus`, `ConfidenceLevel`, `ResolutionOutcome` | Tyler schema enums now live in `tyler_v1_models.py` and drive the Tyler-native runtime stages | Yes |
| Stage 1 decomposition | `DecompositionResult` with `SubQuestion.question`, `research_priority`, `search_guidance`, `ResearchPlan`, `StageSummary` | live runtime now produces and persists `PipelineState.tyler_stage_1_result`; current `QuestionDecomposition` is a compatibility projection | Yes (runtime), compatibility projection remains |
| Stage 2 evidence | `EvidencePackage` made of `SubQuestionEvidence -> Source -> Finding` with `EvidenceLabel` and `quality_score` | live runtime now produces and persists `PipelineState.tyler_stage_2_result`; current `EvidenceBundle` remains the retrieval substrate and compatibility surface | Yes (runtime), compatibility substrate remains |
| Stage 3 analyst output | `AnalysisObject` with `model_alias`, single `recommendation`, Tyler claim/assumption/counterargument shapes, `stage_summary` | live runtime now produces and persists `PipelineState.tyler_stage_3_results`; current `AnalystRun` is an explicit projection | Yes (runtime), compatibility projection remains |
| Stage 4 claim extraction | single Tyler `ClaimExtractionResult` artifact containing `claim_ledger`, `assumption_set`, `dispute_queue`, and `statistics` | Tyler Stage 4 prompt/schema runs in the live runtime and serializes into `PipelineState.tyler_stage_4_result`; current `ClaimLedger` is an explicit downstream projection | Yes (runtime), compatibility projection remains |
| Stage 5 arbitration | `ArbitrationAssessment`, `ClaimStatusUpdate`, `VerificationResult` with post-verification statuses `verified/refuted/unresolved` | Tyler Stage 5 runs in the live runtime and serializes into `PipelineState.tyler_stage_5_result`; current ledger/arbitration surfaces are compatibility projections | Yes (runtime), compatibility projection remains |
| Stage 6 report | Tyler `SynthesisReport` 3-tier schema with `process_summary`, `disagreement_map`, `claim_ledger_excerpt`, `evidence_trail`, etc. | Tyler Stage 6 runs in the live runtime and serializes into `PipelineState.tyler_stage_6_result`; current `FinalReport` and markdown report are compatibility projections | Yes (runtime), compatibility projection remains |
| Prompt package | Tyler literal prompts by stage and frame | Tyler-native prompt surfaces are active for Stages 1-6, but the tracked UBI rerun still regressed in usefulness, so literal prompt fidelity must now be audited stage by stage | Runtime-active, quality still under audit |

## Current Prompt Inventory vs Tyler Prompt Inventory

| Tyler prompt surface | Current prompt surface | Status |
|---|---|---|
| Stage 1 decomposition | `prompts/tyler_v1_decompose.yaml` | Literal prompt now active in runtime |
| Stage 2 finding extraction | `prompts/tyler_v1_extract_findings.yaml` | Literal prompt now active in runtime |
| Stage 2 query diversification | `prompts/tyler_v1_query_diversification.yaml` | Literal prompt now active in runtime |
| Stage 3 analyst base + 3 frame inserts | `prompts/tyler_v1_analyst.yaml` | Literal prompt now active in runtime |
| Stage 4 claim extraction + dispute localization | `prompts/tyler_v1_stage4.yaml` | Literal prompt/schema now active, but downstream stages still rely on a projected repo-local ledger |
| Stage 5 verification query generation | `prompts/verification_queries.yaml` | Adapted, not literal |
| Stage 5 arbitration | `prompts/tyler_v1_arbitration.yaml` | Literal prompt active, projected into current compatibility surfaces |
| Stage 6 synthesis report | `prompts/tyler_v1_synthesis.yaml` | Literal prompt active, projected into current compatibility surfaces |

## Exact Remaining Non-Literal Gaps That Matter

### 1. Compatibility projections still coexist

The live runtime is Tyler-native, but the repo still keeps compatibility
projections for:

- `QuestionDecomposition`
- `EvidenceBundle`
- `AnalystRun`
- `ClaimLedger`
- `FinalReport`

These no longer define the live Tyler runtime, but they still exist for
historical traces and downstream compatibility.

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

So the next local frontier is no longer contract migration, and it is no longer
an unclassified prompt crisis either. The remaining difference is now a narrow,
evidence-backed divergence between the Tyler-native path and the prior
benchmark-optimal dense-dedup path.

## Recommendation

Do not claim full Tyler closure yet.

The correct next move is the prompt-quality recovery wave:

1. audit literal prompt fidelity stage by stage
2. identify the weakest Tyler-native stages on the tracked UBI rerun
3. rerun the same benchmark after local quality recovery

Those steps are captured in:

- `docs/plans/tyler_literal_parity_refactor.md`
- `docs/plans/tyler_literal_parity_benchmark_reanchor.md`
- `docs/plans/tyler_literal_prompt_quality_recovery.md`
