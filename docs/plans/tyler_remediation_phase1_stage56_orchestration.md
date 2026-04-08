# Tyler Remediation Phase 1: Stage 6a / Stage 5 Orchestration

`docs/PLAN.md` remains the canonical repo-level plan. This file is the first
child implementation wave under `tyler_gap_remediation_wave1.md`.

**Status:** Planned
**Type:** implementation
**Priority:** High
**Blocked By:** `docs/plans/tyler_gap_remediation_wave1.md`
**Blocks:** truthful Tyler Stage 4→5→6 behavior

---

## Goal

Patch the first audited Tyler divergences in the live orchestration path:

- `S6A-STEERING-001`
- `S5-ROUND-CAP-001`
- `S5-ORDER-RANDOMIZATION-001`

This wave is first because it fixes a critical end-to-end control-flow bug and
removes one of the biggest remaining ways the repo can claim Tyler behavior
while skipping it in live execution.

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`
- `engine.py`
- `src/grounded_research/verify.py`
- `tests/test_verify.py`
- `tests/test_phase_boundaries.py`
- Tyler packet under `tyler_response_20260326/`

If this plan and the ledger disagree, trust the ledger.

---

## Scope

### In Scope

1. move Stage 6a user steering to the correct point in `run_pipeline()`
2. fix the Stage 6a dispute filter so Tyler-routed disputes actually surface
3. enforce Tyler's hard max-2-round Stage 5 cap regardless of depth profile
4. randomize analyst-position order per dispute before Stage 5 arbitration
5. add targeted tests and at least one phase-boundary check for those behaviors

### Out of Scope

1. Stage 4 randomization
2. Stage 5 query-role correction
3. Stage 6 source propagation / compaction / model-policy correction
4. Stage 1/2 and Stage 3 fixes
5. broad cleanup beyond what is needed to patch these behaviors

---

## Pre-Made Decisions

1. Stage 6a runs after Stage 5 when Stage 5 ran, otherwise after Stage 4.
2. Stage 6a must inspect the latest dispute queue:
   - `stage_5_result.updated_dispute_queue` if present
   - else `stage_4_result.dispute_queue`
3. Stage 6a dispute selection should be status-aware for Tyler-routed disputes:
   - include unresolved decision-critical preference/spec/other disputes
   - include `deferred_to_user` decision-critical preference/spec/other disputes
4. The Stage 5 hard cap is 2 total rounds even if a depth profile asks for
   more. Config may be more restrictive, not less restrictive.
5. Stage 5 randomization must preserve the same dispute content while shuffling
   position order before prompt rendering.
6. Randomization should be implemented in a small pure helper in `verify.py`,
   not inline in the LLM call body.
7. This wave should not introduce new compatibility artifacts or runtime modes.

---

## Implementation Sketch

### Step 1: Stage 6a sequencing

In `engine.py`:

- run Stage 5 first
- then perform the Stage 6a user-steering pass against the updated queue
- keep the existing TTY guard and prompt interaction behavior

### Step 2: Stage 6a dispute filtering

Define a narrow local helper or inline filter that:

- selects `type in {"preference_weighted", "spec_ambiguity", "other"}`
- requires `decision_critical`
- allows `status in {"unresolved", "deferred_to_user"}`

### Step 3: Stage 5 hard round cap

In `verify.py`:

- clamp the configured `arbitration_max_rounds` to `2`
- preserve lower configured values

### Step 4: Stage 5 prompt-order randomization

In `verify.py`:

- create a helper that randomizes the analyst-position presentation order in a
  dispute payload before prompt rendering
- keep the same claims/positions, only reorder their prompt presentation

If the randomization boundary becomes too tangled, use
`docs/plans/post_audit_maintainability_wave1.md` only for a small pure-helper
extraction.

---

## Success Criteria

Pass only if all of the following are true:

1. Stage 6a now runs after Stage 5 in the live pipeline path when Stage 5 runs
2. Tyler-routed `deferred_to_user` disputes actually surface to the steering path
3. Stage 5 never exceeds 2 rounds total
4. Stage 5 arbitration no longer preserves fixed analyst-position order by default
5. tests prove the behavior instead of relying only on static reading

---

## Required Tests

| Test / Check | What It Verifies |
|--------------|------------------|
| targeted `tests/test_verify.py` additions | round-cap enforcement and arbitration randomization |
| targeted `tests/test_phase_boundaries.py` or `tests/test_engine.py` addition | Stage 6a runs after Stage 5 and sees the updated dispute queue |
| one existing verify/export/phase-boundary subset | no regression in the current Tyler path |

---

## Failure Modes

1. Moving Stage 6a but still filtering only `unresolved`
2. Clamping the round cap in config docs but not in live code
3. Randomizing a copied structure that never reaches the prompt
4. Introducing nondeterministic tests without a controllable seed/patch point

---

## Exit Condition

This wave is complete when:

- the three target rows above are patched locally,
- the ledger/status surface can truthfully downgrade or close them,
- and the next remediation child wave can start on Stage 4 or Stage 6 with
  the orchestration path no longer lying about Stage 6a / Stage 5 behavior.
