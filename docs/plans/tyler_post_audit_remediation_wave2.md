# Tyler Post-Audit Remediation Wave 2

`docs/PLAN.md` remains the canonical repo-level plan. This file turns the
post-exhaustive-audit ledger rows into the new local remediation sequence.

**Status:** Active
**Type:** design
**Priority:** High
**Blocked By:** `docs/TYLER_SPEC_GAP_LEDGER.md`
**Blocks:** Remaining local Tyler remediation implementation waves

---

## Goal

Patch the remaining verified local Tyler divergences after the exhaustive
packet audit, without reopening already-closed local waves or mixing shared
infrastructure work back into `grounded-research`.

Phase 1 of this wave landed on 2026-04-13 and closed:

1. `S6-PROMPT-VARS-001`
2. `S5-S6-DATASTRUCT-001`

The active local frontier is now exactly:

1. `SC-PIPELINESTATE-001`
2. `S6-GROUNDING-001`
3. `S6-VALIDATION-COVERAGE-001`

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md`
- `docs/plans/tyler_full_spec_exhaustive_audit_wave1.md`
- Tyler packet under `2026_0325_tyler_feedback/`

If this plan and the ledger disagree, trust the ledger.

---

## Scope

### In Scope

Verified **local** divergences still open after exhaustive packet coverage:

1. Tyler `PipelineState` trace parity
2. Stage 6 grounding reject-and-retry
3. Stage 6 final-report validation coverage

### Out of Scope

- shared provider/runtime/model work
- new benchmark expansion
- broad cleanup unrelated to the three rows above
- reopening already-fixed Stage 1-5 remediation rows

---

## Pre-Made Decisions

1. Fix order follows dependency order, not row order.
2. Stage 5/6 prompt-interface parity lands before Stage 6 validation changes.
3. Stage 6 grounding/validation remediation lands before `PipelineState`
   trace-parity work, so the trace contract reflects the corrected Stage 6
   behavior instead of serializing another intermediate shape.
4. Prompt-side parity means the live prompt/orchestrator interface matches
   Tyler's packet, not merely that the generated prose remains semantically
   similar.
5. Tyler ambiguities stay documented as ambiguities; they do not become local
   pseudo-fixes.
6. No new compatibility surface is allowed. Delete or replace, do not add
   dual paths.

---

## Execution Order

### Phase 1: Stage 5/6 Prompt Contract Parity

**Status:** Completed on 2026-04-13

Rows:

- `S6-PROMPT-VARS-001`
- `S5-S6-DATASTRUCT-001`

Primary surfaces:

- `prompts/tyler_v1_arbitration.yaml`
- `prompts/tyler_v1_synthesis.yaml`
- `src/grounded_research/verify.py`
- `src/grounded_research/export.py`
- prompt render / export tests

Pass if:

- Stage 5 uses Tyler's dict-style `claim_ledger[claim_id]` access contract
- Stage 6 uses `claim_ledger` + `decision_critical_claim_ids`
- Stage 6 user steering uses `user_response_for_dispute`, not the current
  local `stage_6_user_input` prompt interface
- compaction preserves the Tyler-style prompt contract instead of pre-splitting
  prompt inputs into local convenience subsets

Failure modes:

- only the prompt files change while orchestrator kwargs stay local-shaped
- compaction silently reintroduces the old split prompt surface
- Stage 5 dict access breaks arbitration prompt rendering

### Phase 2: Stage 6 Validation Behavior Parity

**Status:** Active

Rows:

- `S6-GROUNDING-001`
- `S6-VALIDATION-COVERAGE-001`

Primary surfaces:

- `src/grounded_research/export.py`
- `engine.py`
- Stage 6 validation tests

Pass if:

- grounding failures feed back into the Stage 6 repair loop once
- the live Stage 6 validation layer enforces Tyler's remaining explicit
  final-report checks, not only the current zombie/underfilled subset

Failure modes:

- grounding remains post-hoc warning-only
- new validation checks exist only in prose, not in the repair loop
- validation logic becomes so strict that valid saved fixtures can no longer
  complete without a corresponding schema/prompt fix

### Phase 3: Tyler `PipelineState` Trace Parity

**Status:** Planned

Rows:

- `SC-PIPELINESTATE-001`

Primary surfaces:

- `engine.py`
- `src/grounded_research/models.py`
- `src/grounded_research/tyler_v1_models.py`
- output/trace tests or artifact checks

Pass if:

- `trace.json` serializes Tyler's `PipelineState` contract rather than the
  current repo-local runtime object
- the serialized trace contains Tyler's top-level stage/result fields,
  `stage_5_skipped`, `stage_6_user_input`, `errors`, and `total_cost_usd`
- partial-trace-on-abort behavior still works after the contract switch

Failure modes:

- trace parity is faked by docs only
- trace generation loses partial-abort state
- the runtime starts keeping two co-equal trace contracts

---

## Verification

Each phase needs:

1. targeted unit tests
2. at least one prompt-render, export-artifact, or phase-boundary check
3. ledger/status doc updates if row status changes

Run `./.venv/bin/python scripts/sync_plan_status.py --check` after each docs
change set.

---

## Exit Condition

This plan is complete when:

- the three rows above have either been fixed or explicitly reclassified by
  evidence,
- `docs/TYLER_EXECUTION_STATUS.md` no longer lists them as active local gaps,
- and the repo-local Tyler frontier returns to either zero active implementation
  gaps or a strictly smaller, evidence-backed set.
