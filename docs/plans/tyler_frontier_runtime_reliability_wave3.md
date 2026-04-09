# Tyler Frontier Runtime Reliability Wave 3

**Status:** Active
**Type:** shared-runtime investigation
**Priority:** High
**Parent plan:** `docs/plans/tyler_shared_parity_closure_wave1.md`

## Goal

Turn the remaining frontier-runtime row from a vague intermittent issue into one
of:

1. a reproducible shared-runtime defect with an owner and patch path, or
2. a narrower documented model-availability limitation with an explicit policy.

This wave exists because the current Tyler-required frontier row is no longer
"untested," but it is not yet closed:

- one literal run failed on Claude Opus Stage 3 citation-floor behavior
- two later literal runs passed on the same intended primary stack

That is enough to rule out a dead config, but not enough to claim stable shared
runtime parity.

## Scope

In scope:

- compare the failed and passing frontier validation runs clause by clause
- identify whether the remaining issue is:
  - provider/runtime behavior,
  - model variability,
  - shared retry/fallback/policy behavior,
  - or a still-hidden local quality-floor sensitivity
- document the exact next owner

Out of scope:

- reopening local Tyler prompt/schema cutover work without evidence
- additional frozen-eval breadth
- broad model benchmarking outside the recorded Tyler frontier row

## Pre-Made Decisions

1. Start from existing recorded runs, not fresh speculation.
2. Use:
   - `output/tyler_frontier_runtime_validation_wave1/`
   - `output/tyler_frontier_runtime_validation_wave2_repeat/`
   - `output/tyler_frontier_runtime_validation_wave2_palantir/`
3. If evidence points to shared runtime behavior, the owner is `llm_client`.
4. If evidence points only to unstable primary-model behavior with no shared
   runtime defect, document it as a model-availability/policy limitation.
5. Do not change `grounded-research` local behavior unless the comparison
   proves a repo-local defect.

## Success Criteria

This wave passes only if:

1. the remaining frontier row has a narrower, evidence-backed classification,
2. the next owner is explicit,
3. `grounded-research` docs stop describing the row generically as
   "intermittent" without further decomposition.

## Phases

### Phase 1: Compare Recorded Runs

Deliverables:

- side-by-side comparison of failed vs passing frontier runs
- exact failing stage, artifact, and policy surface

### Phase 2: Classify The Remaining Issue

Deliverables:

- one of:
  - shared-runtime defect
  - model-availability limitation
  - local-quality-floor sensitivity

### Phase 3: Open The Correct Next Lane

Deliverables:

- docs updated with exact next owner
- if needed, child shared plan in the owning repo

## Verification

Minimum verification:

1. artifact comparison uses recorded `trace.json`, `summary.md`, and
   `llm_observability.db`
2. the final classification cites concrete evidence, not conjecture

## Todo List

- [ ] Phase 1: compare recorded runs
- [ ] Phase 2: classify the remaining issue
- [ ] Phase 3: open the correct next lane
