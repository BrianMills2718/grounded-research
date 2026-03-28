# Isolated Compatibility Surface Deletion

**Status:** In Progress
**Purpose:** Delete non-live compatibility APIs so `main` keeps one canonical
runtime vocabulary instead of a Tyler-native runtime plus a second dormant
current-shape implementation.

## Why This Plan Exists

The live engine now runs Tyler Stage 1-6 directly. What remains is isolated
compatibility code outside the live path:

- current-shape Stage 1 helpers in `decompose.py`
- legacy `AnalystRun`-based analyst execution in `analysts.py`
- current-shape claim-extraction helpers and adapter-only tests
- authority docs that still describe a mixed runtime

This debt no longer protects the live system. It mainly makes the repo harder
for agents to reason about.

## Canonical Decisions

1. `main` keeps one canonical runtime vocabulary: Tyler Stage 1-6.
2. Older tuned/current-shape variants are preserved by commit references and
   eval artifacts, not by keeping a second runnable path in `main`.
3. Delete compatibility execution code before deleting pure helper models.
4. If a helper is still needed only for tests, either move it into the relevant
   test file or delete the test.

## Acceptance Criteria

This wave is complete only if:

1. `engine.py` and live runtime modules expose only Tyler-native execution
   entrypoints
2. `decompose.py` no longer exports current-shape runtime entrypoints
3. `analysts.py` no longer exports the legacy `AnalystRun` execution path
4. active docs no longer describe `QuestionDecomposition` / `AnalystRun` as
   part of the live pipeline
5. targeted decompose/analyst/canonicalize/export/phase-boundary tests pass

## Ordered Phases

### Phase 1: Delete current-shape Stage 1 runtime entrypoints

- remove `decompose_question()`
- remove `decompose_with_validation()`
- keep only Tyler-native decomposition entrypoints plus validation support

Files:

- `src/grounded_research/decompose.py`
- tests covering decomposition runtime

### Phase 2: Delete legacy Stage 3 execution path

- remove `run_analyst()` and `run_analysts()` from the live module surface
- remove `prompts/analyst.yaml` if no live call path remains
- keep only Tyler Stage 3 execution plus `stage3_attempts`

Files:

- `src/grounded_research/analysts.py`
- `prompts/analyst.yaml`
- `tests/test_analysts.py`

### Phase 3: Delete current-shape Stage 3/3a compatibility helpers

- remove compatibility-only `AnalystRun` projections from live helper modules
- remove `extract_raw_claims()` if it is no longer part of any live or
  benchmark-supported path
- delete adapter-only tests that exist solely for the removed path

Files:

- `src/grounded_research/canonicalize.py`
- `src/grounded_research/tyler_v1_adapters.py`
- `tests/test_canonicalize.py`
- `tests/test_tyler_v1_stage3_adapters.py`

### Phase 4: Rewrite authority docs and commit map

- update `docs/CONTRACTS.md`, `docs/PLAN.md`, `docs/ARCHITECTURE_ONE_PAGE.md`,
  `docs/ROADMAP.md`, `docs/TYLER_LITERAL_PARITY_AUDIT.md`,
  `docs/TYLER_VARIANT_COMMIT_MAP.md`, and the plan index
- record the last commit that still contained the removed compatibility path

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| Deleting compatibility entrypoints breaks still-live tests | targeted decompose/analyst tests fail immediately | delete or rewrite those tests to target the Tyler-native path instead of restoring the runtime path |
| A supposedly isolated helper is still used by the engine | compile or phase-boundary tests fail | restore only the narrow helper dependency, not the broader legacy path, then open a follow-up child slice |
| Authority docs still describe mixed runtime contracts | grep still finds `AnalystRun` / `QuestionDecomposition` in active docs | rewrite the doc section immediately; do not defer doc cleanup |
