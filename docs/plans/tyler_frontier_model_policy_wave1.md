# Tyler Frontier Model Policy Wave 1

**Status:** Completed
**Type:** shared-policy plan
**Priority:** High
**Parent plan:** `docs/plans/tyler_frontier_runtime_reliability_wave3.md`

## Goal

Define the explicit policy for handling the remaining Tyler frontier-model row
after the runtime investigation showed model-output variability rather than a
transport or schema defect.

This wave exists because the remaining open item is no longer "why did the run
fail?" The answer is now known:

- the shared runtime worked,
- the configured primary model stack was callable,
- one Claude Opus Stage 3 response on the PFAS fixture returned one uncited
  claim that the local citation floor correctly rejected,
- later runs on the same intended stack passed.

So the unresolved question is now policy:

- when do we keep Tyler's intended primary stack despite stochastic misses?
- when do we change the stack or add extra shared safeguards?

## Scope

In scope:

- define the evidence threshold for changing the Tyler-intended primary stack
- define what counts as a model-policy limitation vs a shared-runtime defect
- define the allowed mitigation types

Out of scope:

- changing `grounded-research` local stage logic without new evidence
- ad hoc model swaps based on one failed run
- broad benchmark expansion

## Pre-Made Decisions

1. One stochastic quality-floor miss is not enough to replace Tyler's intended
   primary model stack.
2. Shared-runtime defects and model-output variability must stay separate:
   - runtime defects belong in `llm_client`
   - model-output variability belongs in shared model/config policy
3. Allowed mitigation types, in priority order:
   - document the limitation and keep the stack
   - add repeatability/health policy in shared config surfaces
   - only then consider changing the default primary model stack
4. No repo-local workaround in `grounded-research` should be added for this row
   unless a later run proves a local defect.

## Policy Decision

Use this rule for Tyler frontier-stack changes:

1. **Do not change the primary stack after one stochastic quality-floor miss.**
2. Escalate from "document and keep the stack" to "consider a stack change"
   only if one of these thresholds is met:
   - the same model-role pair fails the same quality floor in at least `2/3`
     identical reruns on the same fixture, or
   - the same failure mode appears on at least `2` distinct fixtures, or
   - a shared transport/schema/runtime defect is proven.
3. Before any stack change, allowed mitigations are:
   - rerun the identical fixture,
   - run one additional distinct fixture,
   - inspect the raw response to separate runtime defects from model-output
     variability,
   - if needed, add shared health/policy handling outside
     `grounded-research`.
4. A primary-stack change is a last resort, not the first response.

## Success Criteria

This wave passes only if:

1. the remaining frontier row has an explicit policy owner and decision rule,
2. the repo no longer leaves the row as an open-ended qualitative concern,
3. any future stack change must point back to this policy rule rather than a
   one-off judgment call.

## Phases

### Phase 1: Define Change Threshold

Deliverables:

- explicit threshold for when model variability justifies changing the primary
  stack

### Phase 2: Define Allowed Shared Mitigations

Deliverables:

- explicit list of acceptable mitigations before a model swap

### Phase 3: Wire Policy Into Status Surfaces

Deliverables:

- status docs and ledger next-action updated to cite this policy

## Verification

Minimum verification:

1. policy cites the recorded frontier evidence
2. ledger/status surfaces reference the policy explicitly

## Todo List

- [x] Phase 1: define change threshold
- [x] Phase 2: define allowed shared mitigations
- [x] Phase 3: wire policy into status surfaces

## Outcome

The policy is now explicit.

Current decision:

- keep Tyler's intended frontier primary stack for now

Why:

- the recorded failure was one stochastic Claude Opus Stage 3 citation-floor
  miss
- the same stack passed on the next PFAS repeat
- the same stack also passed on the Palantir fixture
- no shared transport/schema/runtime defect was demonstrated
