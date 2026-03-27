# Tyler Literal Parity Stage 1-3 Native Migration

**Status:** In Progress
**Parent plan:** `docs/plans/tyler_literal_parity_refactor.md`
**Purpose:** Replace the remaining adapter-fed upstream runtime surfaces with
native Tyler Stage 1, Stage 2, and Stage 3 artifacts, then re-anchor Stage 4-6
on those persisted artifacts.

## Why This Wave Exists

The runtime now stores Tyler-native Stage 4, Stage 5, and Stage 6 outputs.

Literal parity is still incomplete because the upstream stages still originate
in repo-local contracts:

- Stage 1 still produces `QuestionDecomposition`
- Stage 2 still produces `EvidenceBundle`
- Stage 3 still produces `AnalystRun`

Those current artifacts are then adapted into Tyler-native shapes. That is no
longer acceptable for literal parity.

## Scope

This wave covers repo-local runtime migration for:

1. native Tyler Stage 1 production and persistence
2. native Tyler Stage 2 production and persistence
3. native Tyler Stage 3 production and persistence
4. downstream consumption of the persisted Tyler Stage 1-3 artifacts by the
   already-migrated Tyler Stage 4-6 runtime path

This wave does **not** pull shared-infra gaps back into this repo:

- Tavily/Exa adapters remain `open_web_retrieval`
- provider/runtime behavior studies remain `llm_client` / `prompt_eval`

## Pre-Made Decisions

1. Keep the current runtime artifacts only as explicit compatibility
   projections until the full wave verifies.
2. Persist Tyler Stage 1-3 artifacts in `PipelineState` immediately when they
   are produced.
3. Stage 1 compatibility projection remains `QuestionDecomposition` because
   collection and existing CLI fixtures still require it during migration.
4. Stage 2 keeps `EvidenceBundle` as the mechanical retrieval substrate, but
   the live Stage 2 semantic artifact becomes Tyler `EvidencePackage`.
5. Stage 3 keeps `AnalystRun` as a compatibility surface only; the live Stage 3
   semantic output becomes Tyler `AnalysisObject`.
6. Stage 4, Stage 5, and Stage 6 must prefer persisted Tyler Stage 1-3
   artifacts when present and only adapt from current surfaces when necessary
   for historical-trace compatibility.
7. Do not delete current compatibility projections in this wave. First make the
   native Tyler path live, benchmark it, and verify trace serialization.

## Acceptance Criteria

This wave is complete only if:

1. `PipelineState` persists Tyler-native Stage 1, Stage 2, and Stage 3
   artifacts.
2. Raw-question runs call Tyler-native Stage 1 prompts and persist the Tyler
   result before compatibility projection.
3. Stage 2 uses Tyler query diversification and Tyler finding extraction prompt
   surfaces in the live runtime, then persists Tyler `EvidencePackage`.
4. Stage 3 uses Tyler analyst prompts in the live runtime and persists Tyler
   `AnalysisObject` results plus alias mapping.
5. Stage 4, Stage 5, and Stage 6 use persisted Tyler Stage 1-3 artifacts when
   present.
6. End-to-end trace state for a current run contains Tyler Stage 1-6 artifacts.
7. The targeted Tyler parity test suite passes.

## Execution Order

### Slice 1: Plan + Persistence Surfaces

Files:

- `CLAUDE.md`
- `AGENTS.md`
- `docs/PLAN.md`
- `docs/plans/CLAUDE.md`
- `docs/plans/tyler_literal_parity_refactor.md`
- `docs/notebooks/15_tyler_literal_parity_stage123_native.ipynb`
- `src/grounded_research/models.py`

Decisions:

- add `tyler_stage_1_result`
- add `tyler_stage_2_result`
- add `tyler_stage_3_alias_mapping`
- add `tyler_stage_3_results`

Acceptance:

- planning surfaces are current
- `PipelineState` can serialize the new Tyler Stage 1-3 fields

### Slice 2: Stage 1 Native Decomposition

Files:

- `src/grounded_research/decompose.py`
- `engine.py`
- tests covering decomposition persistence and compatibility projection

Decisions:

- `decompose_with_validation()` becomes Tyler-native internally
- validation continues against the projected current `QuestionDecomposition`
- question-mode runs persist both Tyler Stage 1 and the current projection

Acceptance:

- Stage 1 prompt surface is Tyler-native at runtime
- raw-question path persists `tyler_stage_1_result`
- existing consumers still receive projected `QuestionDecomposition`

### Slice 3: Stage 2 Native Evidence Package

Files:

- `src/grounded_research/collect.py`
- `engine.py`
- `src/grounded_research/tyler_v1_adapters.py`
- tests for Tyler Stage 2 runtime generation

Decisions:

- retrieval remains mechanical and shared-infra-backed
- semantic Stage 2 output becomes Tyler `EvidencePackage`
- keep `EvidenceBundle` for compatibility and for fetch/storage grounding

Acceptance:

- live query diversification uses Tyler prompt surfaces
- live finding extraction uses Tyler prompt surfaces
- Stage 2 persists `tyler_stage_2_result`

### Slice 4: Stage 3 Native Analysis Objects

Files:

- `src/grounded_research/analysts.py`
- `engine.py`
- tests for Tyler Stage 3 runtime generation

Decisions:

- analysts still run independently and anonymously
- live Stage 3 output becomes Tyler `AnalysisObject`
- current `AnalystRun` remains compatibility projection only

Acceptance:

- Stage 3 prompt surface is Tyler-native at runtime
- Stage 3 persists `tyler_stage_3_results` and alias mapping

### Slice 5: Downstream Re-Anchor + Gate

Files:

- `src/grounded_research/canonicalize.py`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`
- `engine.py`
- parity tests

Decisions:

- prefer persisted Tyler Stage 1-3 artifacts over on-the-fly adapters
- keep adapter fallback only for historical traces and fixture compatibility

Acceptance:

- Stage 4-6 read Tyler Stage 1-3 from runtime state when present
- Tyler parity suite passes
- a live smoke or fixture run serializes Stage 1-6 Tyler artifacts together

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| Stage 1 becomes Tyler-native but validation path breaks | decomposition succeeds but validation or collection crashes | keep validation on projected current decomposition while persisting Tyler Stage 1 |
| Stage 2 prompt cutover lowers finding quality or loses provenance | findings become vague or source linkage breaks | fail the slice and tighten the Tyler extraction contract before proceeding |
| Stage 3 Tyler-native analyses break Stage 4 assumptions | Stage 4 schema passes but claim/dispute quality collapses | verify Stage 4 against persisted Tyler Stage 3 before deleting any compatibility path |
| downstream stages silently keep using adapters | trace shows Tyler Stage 1-3 persisted but Stage 4-6 still regenerate them | add explicit preference order and tests for persisted-artifact consumption |
| full literal parity regresses benchmark usefulness | parity suite passes but report quality falls materially | record the divergence explicitly; do not hide it behind projections |

## Verification

Required deterministic suite:

- `tests/test_tyler_v1_models.py`
- `tests/test_tyler_v1_adapters.py`
- `tests/test_tyler_v1_stage2_adapters.py`
- `tests/test_tyler_v1_stage3_adapters.py`
- `tests/test_tyler_v1_stage4_adapters.py`
- `tests/test_tyler_v1_stage5_6_adapters.py`
- `tests/test_phase_boundaries.py`
- any new Stage 1-3 native runtime tests added in this wave

Required live gate:

- one fixture or small-question smoke with trace serialization proving Tyler
  Stage 1-6 artifacts coexist in the same run

## Repo-Local Done Line

Repo-local Tyler literal parity for this project is complete when:

1. Stages 1-6 are Tyler-native in the live runtime
2. remaining non-literal gaps are documented as explicit shared-infra
   dependencies
3. no stage claims literal parity while still depending on silent adapter-fed
   upstream inputs
