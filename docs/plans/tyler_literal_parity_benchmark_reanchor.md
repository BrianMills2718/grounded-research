# Tyler Literal Parity Benchmark Re-Anchor

**Status:** In Progress
**Parent plan:** `docs/plans/tyler_literal_parity_refactor.md`
**Purpose:** Re-anchor the tracked benchmark surfaces on the fully Tyler-native
runtime and make any remaining divergence explicit instead of leaving literal
parity as a purely schema-level claim.

## Why This Wave Exists

The repo-local runtime now persists Tyler Stage 1 through Stage 6 artifacts.

That is necessary, but not sufficient. The project still needs a benchmark gate
that answers:

1. does the live Tyler-native pipeline serialize all six stages in a real run?
2. does literal parity preserve or improve the tracked benchmark anchors?
3. if it regresses, is the regression a local contract issue or an external
   provider/runtime issue?

## Scope

This wave covers:

1. one completed Tyler-native smoke run proving Stage 1-6 trace serialization
2. one tracked benchmark rerun on the Tyler-native path
3. explicit recording of any divergence between literal parity and current
   decision-usefulness anchors

This wave does **not** treat provider stalls or search-provider parity as local
product bugs when they are shared-infra issues.

## Pre-Made Decisions

1. Use the small `session_storage_bundle.json` fixture as the first smoke gate.
2. Use the existing tracked UBI/session benchmark surfaces after the smoke
   passes.
3. A provider stall without a local code failure is logged as a runtime/shared
   infra issue, not silently ignored and not misclassified as a local parity
   failure.
4. Do not reopen Stage 1-6 contract work unless the benchmark exposes a real
   local artifact bug.

## Acceptance Criteria

This wave is complete only if:

1. at least one current run writes a `trace.json` containing Tyler Stage 1-6
   artifacts
2. one tracked benchmark rerun completes on the Tyler-native path
3. the result is written down explicitly as one of:
   - parity preserved usefulness
   - parity improved usefulness
   - parity regressed usefulness
4. any unresolved gap is tagged as repo-local or shared-infra, not left
   ambiguous

## Execution Order

## Next 24 Hours

Treat the next 24 hours as one continuous closure wave:

1. complete one Tyler-native smoke trace on a small fixture
2. rerun one tracked benchmark fixture on the Tyler-native runtime
3. compare the result to the current saved anchor
4. if a local artifact bug appears, fix it and rerun the same gate
5. if only provider/runtime stalls remain, record them as shared-infra
   blockers and close the repo-local wave honestly

### Slice 1: Smoke Gate

- run `engine.py --fixture tests/fixtures/session_storage_bundle.json`
- require a `trace.json` with Tyler Stage 1-6 fields
- require Tyler Stage 4 to produce a non-empty claim/assumption artifact when
  Stage 3 produced extractable assertions

If it fails:

- if code-level: fix locally
- if provider/runtime stall only: record and continue to shared-infra boundary

Operational rule:

- allow the run to continue through the configured timeout window before
  classifying it as stalled
- inspect `llm_observability.db` before making any diagnosis

### Slice 2: Tracked Benchmark Rerun

- rerun the tracked benchmark on the Tyler-native runtime
- compare to the current calibrated anchor

Current benchmark target:

- use the saved UBI economics anchor as the tracked benchmark surface first

### Slice 3: Record Outcome

- update `docs/TYLER_LITERAL_PARITY_AUDIT.md`
- update `docs/plans/tyler_literal_parity_refactor.md`
- update `docs/PLAN.md` and `docs/plans/CLAUDE.md`

## Failure Modes

| Failure mode | What it looks like | Response |
|---|---|---|
| late provider stall | live run reaches a long structured call and never returns promptly | record as shared-runtime uncertainty; do not reopen schema migration |
| schema-valid empty Tyler Stage 4 artifact | Stage 4 returns `claim_ledger=[]` and `assumption_set=[]` despite non-empty Stage 3 analyses | retry with the configured stronger Stage 4 model; fail loud if retry is still empty |
| near-miss Stage 4 schema failure | primary Stage 4 output contains real claims but misplaces disputes/assumptions or omits required fields | retry with the configured stronger Stage 4 model using the concrete validation failure summary |
| cheap-model Stage 4 timeout | the primary Stage 4 model never returns inside the configured window on dense fixtures | promote the already-proven stronger Stage 4 model to primary config, keep the cheaper model only as fallback |
| benchmark regression after literal parity | Tyler-native path loses decision usefulness | record the divergence explicitly and isolate whether it is prompt/provider behavior or local contract logic |
| silent fallback to current artifacts | smoke trace lacks Tyler stage fields even though tests pass | treat as local bug and reopen runtime wiring |
