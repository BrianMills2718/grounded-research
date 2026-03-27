# Tyler Literal Parity Refactor

**Status:** In Progress
**Purpose:** Replace the current adapted Tyler-alignment layer with literal
implementation of Tyler's `V1_SCHEMAS` and `V1_PROMPTS` contracts where that is
repo-local work, and make any remaining non-literal gaps explicit shared-infra
dependencies rather than silent divergence.

## Why This Plan Exists

The current repo does **not** implement Tyler's schemas and prompts literally.
That is now a user-facing requirement, not a future-alignment candidate.

The gap is real in:

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
4. Keep benchmarks running during migration through adapters or dual-surface
   compatibility where practical.
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

Files likely touched:

- `models.py` or adapters from current runtime
- `decompose.py`
- `collect.py`
- `analysts.py`
- `prompts/decompose.yaml`
- `prompts/extract_evidence.yaml`
- `prompts/query_generation.yaml`
- `prompts/analyst.yaml`

Acceptance:

- Stage 1 returns `DecompositionResult`
- Stage 2 returns `EvidencePackage`
- Stage 3 returns Tyler `AnalysisObject` artifacts

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
- The shipped `ClaimLedger` remains as an explicit projection from the Tyler
  artifact so Stage 5-6 can keep running until their migrations land.

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
- The shipped `ClaimLedger`, `ArbitrationResult`, `FinalReport`, and markdown
  report remain explicit projections from the Tyler artifacts for compatibility
  with the existing downstream surfaces.

### Phase 4: Benchmark Re-Anchor

Re-run the tracked benchmark surfaces on the Tyler-native runtime.

Acceptance:

- end-to-end benchmark traces serialize Tyler-native artifacts
- no hidden adapter-only success masking broken runtime parity

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| schema classes land but runtime never uses them | dead contract module with no migration value | phase-gate the runtime migrations immediately after codification |
| Stage 4 rewrite breaks dispute routing | claim/dispute references stop lining up | migrate Stage 4 with dedicated integrity tests before benchmarking |
| Stage 6 rewrite regresses benchmark quality badly | literal parity lowers decision usefulness | record that literal Tyler parity and current benchmark optimum diverge; do not hide it |
| provider assumptions block literal runtime parity | Tyler prompt/schema contract is ready but Tavily/Exa path is external | mark the repo-local refactor complete up to explicit shared-infra dependency boundary |

## Current Remaining Gap

Literal Tyler parity is still not complete end-to-end because Stages 1-3 remain
adapter-fed rather than native runtime artifacts. The runtime now stores Tyler
Stage 4/5/6 results, but Stage 1 decomposition, Stage 2 evidence collection,
and Stage 3 analyst generation still originate in the shipped repo-local
contracts before being projected into Tyler-native shapes.

## Immediate Next Step

Implement Phase 0 now:

1. add Tyler-native schema classes in code
2. add tests for their literal enum values and basic validation
3. keep current runtime unchanged until the contract target is real
