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

## Pre-Made Decisions

1. `collect.py` will consume Tyler Stage 1 directly in the live path.
2. `QuestionDecomposition` becomes an explicit legacy import/migration surface,
   not an auto-detected live runtime contract.
3. Fixture mode will auto-detect only `tyler_stage_1.json`; legacy
   `decomposition.json` will be loadable only via an explicit flag/path.
4. `PipelineState.analyst_runs` will be removed from the live trace.
5. A lightweight Stage 3 execution-trace surface will replace `analyst_runs`
   for human-readable failure/debug visibility.
6. Phase summaries and tests will derive semantic analyst coverage from Tyler
   Stage 3 `AnalysisObject`s, not from projected `AnalystRun`s.

## Acceptance Criteria

This wave is complete only if:

1. collection and sufficiency checks consume Tyler Stage 1 directly
2. the live engine no longer needs current `QuestionDecomposition` to run
3. the live engine no longer needs projected `AnalystRun` to run
4. active docs describe Tyler Stage 1/3 as the live orchestration contract
5. fixture, collection, analyst, and phase-boundary tests pass on the new path

## Ordered Phases

### Phase 1: Make Stage 1 the live collection contract

- update collection helpers to prefer `DecompositionResult`
- remove `current_decomposition=` from the live Stage 2 build path
- derive sufficiency and sub-question ID logic from Tyler `Q-*` IDs directly

Files:

- `src/grounded_research/collect.py`
- `engine.py`
- `tests/test_tyler_v1_stage2_runtime.py`
- `tests/test_tyler_v1_stage2_adapters.py`

Verification:

- `python -m py_compile src/grounded_research/collect.py engine.py tests/test_tyler_v1_stage2_runtime.py tests/test_tyler_v1_stage2_adapters.py`
- `./.venv/bin/python -m pytest tests/test_tyler_v1_stage2_runtime.py tests/test_tyler_v1_stage2_adapters.py tests/test_collect.py -q`

### Phase 2: Remove live auto-loading of legacy decomposition

- auto-detect only `tyler_stage_1.json` in fixture mode
- keep legacy `decomposition.json` load behind explicit user-provided path only
- update CLI help and fixture tests accordingly

Files:

- `engine.py`
- fixture-loading tests under `tests/`

Verification:

- `python -m py_compile engine.py`
- `./.venv/bin/python -m pytest tests/test_phase_boundaries.py -q`

### Phase 3: Replace `PipelineState.analyst_runs` with Stage 3 execution traces

- add a small non-semantic execution-trace model for analyst attempts
- store labels/model/frame/error/claim_count only
- stop storing projected `AnalystRun` as pipeline state
- derive phase summaries from Tyler Stage 3 results + attempt trace

Files:

- `src/grounded_research/models.py`
- `src/grounded_research/analysts.py`
- `engine.py`
- `tests/test_phase_boundaries.py`
- `tests/test_analysts.py`

Verification:

- `python -m py_compile src/grounded_research/models.py src/grounded_research/analysts.py engine.py tests/test_phase_boundaries.py tests/test_analysts.py`
- `./.venv/bin/python -m pytest tests/test_analysts.py tests/test_phase_boundaries.py -q`

### Phase 4: Make Stage 3 the only live semantic analyst contract

- stop passing projected `AnalystRun` through the live canonicalize path
- canonicalize should use Tyler Stage 3 results + alias mapping directly
- keep any remaining `AnalystRun`-based helpers only in clearly labeled compatibility tests or remove them

Files:

- `engine.py`
- `src/grounded_research/canonicalize.py`
- `tests/test_canonicalize.py`

Verification:

- `python -m py_compile engine.py src/grounded_research/canonicalize.py tests/test_canonicalize.py`
- `./.venv/bin/python -m pytest tests/test_canonicalize.py tests/test_phase_boundaries.py -q`

### Phase 5: Rewrite active docs and commit map

- update the active authority docs to say Stage 1/3 runtime cutover is complete
- record commit anchors for the old projected path

Files:

- `docs/CONTRACTS.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE_ONE_PAGE.md`
- `docs/TYLER_LITERAL_PARITY_AUDIT.md`
- `docs/TYLER_VARIANT_COMMIT_MAP.md`
- `docs/plans/CLAUDE.md`

Verification:

- `rg -n "QuestionDecomposition|AnalystRun" docs/CONTRACTS.md docs/PLAN.md docs/ROADMAP.md docs/ARCHITECTURE_ONE_PAGE.md docs/TYLER_LITERAL_PARITY_AUDIT.md docs/plans/CLAUDE.md`
- any remaining hits in active docs must describe explicit historical or compatibility context only

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| Stage 2 grouping loses sub-question coverage after Stage 1 cutover | Stage 2 tests fail or evidence loses Tyler `Q-*` routing | derive all grouping from Tyler IDs directly and delete current-ID translation from the live path |
| fixture users still rely on `decomposition.json` auto-detect | fixture tests or manual fixture runs fail unexpectedly | keep explicit legacy load path, but do not restore auto-detect |
| removing `analyst_runs` destroys failure/debug visibility | traces become unreadable for failed analysts | add or expand the lightweight Stage 3 execution-trace model; do not restore `AnalystRun` as a semantic stage artifact |
| canonicalize still needs projected `AnalystRun` in the live path | canonicalize tests fail after engine stops passing it | make `canonicalize_tyler_v1()` require Tyler Stage 3 inputs in the live path and keep any `AnalystRun` path only for isolated compatibility tests |
