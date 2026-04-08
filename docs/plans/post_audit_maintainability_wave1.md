# Post-Audit Maintainability Wave 1

`docs/PLAN.md` remains the canonical repo-level plan. This file defines a
strictly limited maintainability wave that exists only to make Tyler
remediation easier to implement, verify, and keep correct.

**Status:** Planned
**Type:** design
**Priority:** Medium
**Blocked By:** `docs/plans/tyler_gap_remediation_wave1.md`
**Blocks:** cleaner execution of later Tyler remediation child waves

---

## Goal

Reduce the parts of `grounded-research` that make audited Tyler fixes harder to
implement and verify.

This is not a generic cleanup plan. It is a remediation-support plan.

---

## Why This Exists

The Tyler audit found failures in these behavior classes:

- stage ordering
- dispute status transitions
- evidence/source propagation
- round caps
- prompt-input randomization

Those are easiest to fix and keep fixed when:

1. stage-boundary assertions exist,
2. the relevant Stage 5 and Stage 6 logic is factored into smaller pure
   functions,
3. the ledger/remediation surfaces are easier to consume programmatically.

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`
- `engine.py`

If this plan conflicts with the Tyler remediation plan, trust the remediation
plan.

---

## Strict Scope

### In Scope

1. stage-boundary assertion helpers for:
   - stage ordering
   - dispute status transitions
   - source propagation
   - round caps
2. refactors in `verify.py` and `export.py` that extract smaller pure functions
   specifically around:
   - Stage 5 query generation
   - Stage 5 round management
   - Stage 6 source assembly
   - Stage 6 compaction/input assembly
3. minimal ledger ergonomics if needed to support remediation execution, such
   as adding machine-readable row tags

### Out of Scope

1. broad file reorganization
2. aesthetic cleanup
3. generic abstraction layers
4. reopening deleted compatibility paths
5. changes that are not directly justified by audited Tyler remediation work

---

## Pre-Made Decisions

1. This wave supports later remediation waves; it does not replace them.
2. No cleanup is justified unless it directly improves remediation correctness
   or verification.
3. `verify.py` and `export.py` are the only worthwhile first refactor targets.
4. Any new helper must make a real behavior assertion or isolate a real
   behavior boundary; otherwise do not add it.
5. Randomization must be explicit and testable:
   - seedable where practical,
   - emitted into trace/state where useful,
   - verified with deterministic tests.
6. If a maintainability improvement can be folded directly into a remediation
   child wave, prefer that over a standalone cleanup patch.

---

## Recommended Execution Order

### Phase 1: Stage-Boundary Assertion Support

Deliverables:

- a small assertion/helper surface for:
  - stage order
  - dispute status transitions
  - round-cap checks
  - source propagation checks

Pass if:

- later remediation waves can verify these behaviors without duplicating custom
  ad hoc assertions in every test

### Phase 2: Stage 5 Refactor Boundary

Deliverables:

- smaller pure helpers inside or beside `verify.py` for:
  - query-role generation
  - dispute-order randomization
  - round-cap enforcement

Pass if:

- the Stage 5 Tyler remediation wave can patch behavior without editing one
  large tangled function body

### Phase 3: Stage 6 Refactor Boundary

Deliverables:

- smaller pure helpers inside or beside `export.py` for:
  - Stage 5 source inclusion
  - synthesis-context compaction/input assembly
  - model-policy selection boundary

Pass if:

- Stage 6 Tyler remediation can be tested as smaller units plus one
  phase-boundary check

### Phase 4: Ledger Ergonomics

Deliverables:

- only if needed, add row tags such as:
  - `root_cause`
  - `verification_kind`
  - `fix_wave`

Pass if:

- remediation planning/status can be derived more mechanically from the ledger

Do not do this phase if the existing markdown ledger is already sufficient for
the active remediation waves.

---

## Verification

This wave is only worth doing if it improves verification.

Required proof for any implementation slice:

1. targeted tests on the new helper/assertion boundary
2. at least one phase-boundary or CLI-path check still passing
3. no new compatibility/dead-code surface introduced

---

## Failure Modes

1. cleanup sprawl disguised as maintainability work
2. extracting helpers that do not correspond to real behavior boundaries
3. adding abstractions that make the code harder for agents to follow
4. opening this wave before the remediation child wave actually needs it

---

## Exit Condition

This wave is complete when one of the following is true:

1. the high-value assertion/refactor surfaces have landed and later Tyler
   remediation waves are easier to execute, or
2. the active remediation waves prove these maintainability changes are
   unnecessary, in which case this plan should be closed without code changes.
