# Stage 1/3 Runtime Projection Cutover

**Status:** In Progress
**Purpose:** Decide and execute the remaining cutover from legacy
`QuestionDecomposition` / `AnalystRun` runtime projections to Tyler Stage 1/3
artifacts as the only live orchestration surfaces.

## Why This Plan Exists

After the export and Stage 4/5 projection deletions, the main remaining
repo-local adapter debt is earlier in the pipeline:

- `collect.py` still consumes `QuestionDecomposition`
- CLI fixture loading still prefers `decomposition.json` in the current shape
- `run_analysts_tyler_v1()` still returns projected `AnalystRun`s and the live
  engine stores them in `PipelineState`
- human-readable summaries and some tests still rely on projected `AnalystRun`
  counts and claims

This is no longer a mechanical deletion. It changes the live orchestration
contract for collection, fixture ingestion, and phase summaries.

## Canonical Decisions

1. Tyler Stage 1 `DecompositionResult` should be the live collection/planning input.
2. Tyler Stage 3 `AnalysisObject` should be the live analyst output surface.
3. Current `QuestionDecomposition` and `AnalystRun` should not remain co-equal
   runtime contracts in `main`.
4. If human-readable summaries need a simpler view, derive them from Tyler
   artifacts locally instead of storing compatibility projections as state.

## Required Design Decisions Before Implementation

1. Whether `collect.py` should accept Tyler Stage 1 directly and treat current
   decomposition as an optional import-only adapter.
2. Whether fixture mode should prefer `tyler_stage_1.json` and stop auto-loading
   `decomposition.json` unless explicitly requested.
3. Whether `PipelineState.analyst_runs` should be removed entirely or retained
   only for explicitly labeled archived traces.
4. How phase-boundary tests should assert analyst coverage once `AnalystRun`
   stops being the primary trace view.

## Acceptance Criteria

This wave is complete only if:

1. collection and sufficiency checks consume Tyler Stage 1 directly
2. the live engine no longer needs current `QuestionDecomposition` to run
3. the live engine no longer needs projected `AnalystRun` to run
4. active docs describe Tyler Stage 1/3 as the live orchestration contract
5. fixture, collection, analyst, and phase-boundary tests pass on the new path

## Current Concern

This wave crosses a real architectural boundary. It is not yet safe to execute
without deciding the collection and fixture contracts above. That concern is
why the parent cutover plan remains open after the export and Stage 4/5 waves.
