# Tyler Literal Parity Refactor

**Status:** Completed for repo-local runtime parity; remaining differences are explicit shared-infra or benchmark-divergence concerns
**Purpose:** Replace the current adapted Tyler-alignment layer with literal
implementation of Tyler's `V1_SCHEMAS` and `V1_PROMPTS` contracts where that is
repo-local work, and make any remaining non-literal gaps explicit shared-infra
dependencies rather than silent divergence.

## Why This Plan Exists

This plan records the repo-local migration that made Tyler-native stage
artifacts and prompt surfaces the live runtime contract in `main`.

The original repo-local gap was real in:

- enums and status lifecycle
- Stage 1 decomposition artifact
- Stage 2 evidence artifact
- Stage 3 analyst artifact
- Stage 4 claim/dispute artifact
- Stage 5 arbitration artifact
- Stage 6 synthesis artifact
- prompt text and stage splitting

Reference audit:

- `docs/TYLER_LITERAL_PARITY_AUDIT.md`

## Scope

This refactor covers repo-local literal parity for:

1. Tyler schema contracts in Python code
2. Tyler prompt texts in `prompts/`
3. runtime stage outputs and validators
4. tests and benchmark harnesses that depend on those contracts

This plan does **not** silently pull shared-infra work back into the repo.

Shared-infra dependencies remain explicit:

- Tavily/Exa adapters: `open_web_retrieval`
- provider/model behavior studies: `llm_client` / `prompt_eval`

## Pre-Made Decisions

1. Treat Tyler's markdown spec as the contract source of truth for this
   refactor.
2. Migrate in phases; do not attempt a big-bang runtime rewrite.
3. Land exact Tyler schema classes in code before rewriting runtime stages.
4. Keep benchmarks running during migration, but remove compatibility surfaces
   aggressively once the Tyler-native path is verified.
5. Stage 4 and Stage 6 are the highest-risk contract migrations and get their
   own dedicated waves.
6. Do not claim full literal parity until the runtime uses Tyler-native stage
   artifacts end-to-end.

## Acceptance Criteria

This refactor is complete only if:

1. Tyler schema classes exist in code and match the spec literally enough for
   direct prompt/schema use.
2. Runtime Stage 1-6 outputs are Tyler-native artifacts, not repo-local
   approximations.
3. The active prompt files are Tyler's literal prompt texts or only differ
   where the Tyler spec explicitly leaves implementation details open.
4. Benchmark and trace outputs use Tyler-native stage artifact shapes.
5. Any remaining gaps are explicitly tagged as shared-infra dependencies, not
   ambiguous local divergence.

## Phases

### Phase 0: Contract Codification

Land exact Tyler V1 schema classes in code without changing runtime behavior
yet.

Files:

- `src/grounded_research/tyler_v1_models.py`
- tests for enum values and core model validation

Acceptance:

- Tyler enum values exist literally in code
- core Tyler models parse minimal valid fixtures

### Phase 1: Stage 1-3 Surface Migration

Migrate decomposition, evidence package construction, and analyst outputs to
Tyler-native artifacts.

Detailed execution plan:

- `docs/plans/tyler_literal_parity_stage123_native.md`
- `docs/notebooks/15_tyler_literal_parity_stage123_native.ipynb`

Acceptance:

- Stage 1 returns `DecompositionResult`
- Stage 2 returns `EvidencePackage`
- Stage 3 returns Tyler `AnalysisObject` artifacts

Status:

- Completed for repo-local runtime output and trace state.
- Tyler Stage 1, Stage 2, and Stage 3 now run as the live runtime artifacts
  and persist into `PipelineState`.
- `QuestionDecomposition` and `AnalystRun` are removed from the live runtime;
  `EvidenceBundle` remains only as the mechanical retrieval substrate feeding
  Tyler Stage 2.

### Phase 2: Stage 4 Major Contract Migration

Rewrite canonicalization around Tyler's literal `ClaimExtractionResult`.

Files likely touched:

- `canonicalize.py`
- `models.py`
- `prompts/tyler_v1_stage4.yaml`
- `tyler_v1_adapters.py`

Acceptance:

- Stage 4 emits Tyler `ClaimLedgerEntry`, `AssumptionSetEntry`,
  `DisputeQueueEntry`, and `ExtractionStatistics`
- referential integrity checks pass

Status:

- Completed for Stage 4 runtime output and trace serialization.
- Current `engine.py` now runs Tyler's literal Stage 4 prompt/schema and stores
  the `tyler_stage_4_result` artifact in pipeline state.
- Current-shape Stage 4 compatibility protocols are removed from `main`.

### Phase 3: Stage 5-6 Major Contract Migration

Replace repo-local arbitration/report surfaces with Tyler-native artifacts.

Files likely touched:

- `verify.py`
- `export.py`
- `prompts/verification_queries.yaml`
- `prompts/arbitration.yaml`
- `prompts/synthesis.yaml`
- `prompts/long_report.yaml`

Acceptance:

- Stage 5 emits Tyler `VerificationResult`
- Stage 6 emits Tyler `SynthesisReport`
- user-steering interrupt logic matches Tyler's trigger contract

Status:

- Completed for Stage 5 and Stage 6 runtime output and trace serialization.
- `engine.py` now runs Tyler-native Stage 5 and Stage 6 contracts and stores
  the results in pipeline state.
- Legacy `ArbitrationResult`, `FinalReport`, and old export/handoff runtime
  surfaces are removed from `main`; markdown now renders from Tyler Stage 6.

### Phase 4: Benchmark Re-Anchor

Re-run the tracked benchmark surfaces on the Tyler-native runtime.

Acceptance:

- end-to-end benchmark traces serialize Tyler-native artifacts
- no hidden adapter-only success masking broken runtime parity
- record explicitly if literal Tyler parity and the current benchmark optimum
  diverge

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| schema classes land but runtime never uses them | dead contract module with no migration value | phase-gate the runtime migrations immediately after codification |
| Stage 4 rewrite breaks dispute routing | claim/dispute references stop lining up | migrate Stage 4 with dedicated integrity tests before benchmarking |
| Stage 6 rewrite regresses benchmark quality badly | literal parity lowers decision usefulness | record that literal Tyler parity and current benchmark optimum diverge; do not hide it |
| provider assumptions block literal runtime parity | Tyler prompt/schema contract is ready but Tavily/Exa path is external | mark the repo-local refactor complete up to explicit shared-infra dependency boundary |

## Current Remaining Gap

Repo-local stage-contract migration is complete, and the follow-on prompt
quality recovery wave is also complete.

The remaining differences are now:

1. explicit shared-infra differences from Tyler's specified provider/model/search stack
2. a small, evidence-backed benchmark divergence between the Tyler-native path
   and the saved dense-dedup benchmark-optimal path
3. remaining prompt-literalness uncertainty for Stage 1, Stage 2, and Stage 5

## Current Stop Line

This plan is complete enough for repo-local implementation.

Do not reopen this refactor unless:

1. a new benchmark identifies a grounded-research-specific regression, or
2. shared-infra work lands that enables closer literal Tyler provider/model parity

The remaining faithful-Tyler execution work is tracked separately in:

- `docs/plans/tyler_faithful_execution_remainder.md`
