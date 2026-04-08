# Tyler Gap Remediation Wave 1

`docs/PLAN.md` remains the canonical repo-level plan. This file turns the
verified Tyler gap ledger into an execution-ready remediation sequence.

**Status:** Planned
**Type:** design
**Priority:** High
**Blocked By:** `docs/TYLER_SPEC_GAP_LEDGER.md`
**Blocks:** Local Tyler remediation implementation waves

---

## Goal

Patch the highest-severity verified local Tyler divergences first, without
mixing in shared-infra work or reintroducing deleted compatibility paths.

This plan exists because the audit is now strong enough to stop asking "are
there really gaps?" and start asking "what is the cleanest verified fix order?"

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/plans/tyler_spec_gap_audit_wave1.md`
- Tyler packet under `tyler_response_20260326/`

If this plan and the ledger disagree, trust the ledger.

---

## Scope

### In Scope

Verified **local** divergences currently recorded in the ledger:

1. Stage 1 validation removal
2. Stage 2 model-driven query diversification
3. Stage 2 query-type routing
4. Stage 2 quality-score pipeline
5. Stage 3 B/C frame-model correction
6. Stage 4 prompt-order randomization
7. Stage 5 query-role correction
8. Stage 5 prompt-order randomization
9. Stage 5 hard max-2-round cap
10. Stage 6a user-steering sequencing
11. Stage 6 evidence-context completeness
12. Stage 6 context-compaction parity
13. Stage 6 non-dominant synthesis-model policy

### Out of Scope

- shared Tavily/Exa adapter surface work
- Gemini strict-schema study
- broader frozen eval expansion
- reintroducing legacy runtime contracts

---

## Pre-Made Decisions

1. Remediation stays delete-first. No compatibility branches.
2. Shared-infra-blocked rows do not get patched locally.
3. Fix order follows dependency order, not severity order alone.
4. Stage 6a sequencing must be fixed before any claim that user steering is
   Tyler-faithful can be made.
5. Stage 2 routing and scoring should be planned separately from Tavily/Exa
   shared adapter upgrades; local code must only consume the shared controls
   that actually exist.
6. Prompt-order randomization is local orchestration work, not shared infra.

---

## Execution Order

### Phase 1: Stage 6a/Stage 5 Orchestration Corrections

Why first:
- fixes a critical live logic bug
- unblocks truthful end-to-end Stage 4→5→6 behavior

Rows:
- `S6A-STEERING-001`
- `S5-ROUND-CAP-001`
- `S5-ORDER-RANDOMIZATION-001`

Execution surface:

- `docs/plans/tyler_remediation_phase1_stage56_orchestration.md`
- `docs/notebooks/37_tyler_remediation_phase1_stage56_orchestration.ipynb`

Pass if:
- Stage 6a reads the post-Stage-5 queue when Stage 5 runs
- preference/spec/other disputes actually surface to the user path
- Stage 5 never exceeds 2 rounds
- arbitration prompt input order is randomized per dispute

### Phase 2: Stage 4 Extraction-Order Correction

Rows:
- `S4-ORDER-RANDOMIZATION-001`

Pass if:
- Stage 4 prompt order is randomized per call
- tests prove the shuffle happens without breaking alias integrity

### Phase 3: Stage 6 Synthesis-Context Corrections

Rows:
- `S6-EVIDENCE-CONTEXT-001`
- `S6-COMPACTION-001`
- `S6-MODEL-POLICY-001`

Pass if:
- Stage 5 additional sources enter synthesis context
- synthesis compaction follows an explicit Tyler-inspired priority rule
- default synthesis-model policy no longer violates the non-dominance rule

### Phase 4: Stage 3 Model Assignment Correction

Rows:
- `S3-FRAME-MODEL-001`

Pass if:
- B/C frame-model mapping matches Tyler's requested assignment as far as the
  currently configured models allow

### Phase 5: Stage 1/2 Retrieval And Scoring Corrections

Rows:
- `S1-VALIDATION-001`
- `S2-QUERY-MODEL-001`
- `S2-ROUTING-001`
- `S2-QUALITY-001`

Pass if:
- Stage 1 validation stage is removed locally
- Stage 2 query diversification is model-driven
- local routing logic matches Tyler as far as shared controls allow
- quality scoring no longer collapses to tier mapping alone

Note:
- this phase may branch if shared Tavily/Exa control gaps materially block a
  clean local implementation

---

## Verification

Each phase needs:

1. targeted unit tests
2. at least one phase-boundary or CLI-path check
3. ledger/status doc update if the row status changes

If a phase is blocked mainly by tangled local verification or function-boundary
issues in `verify.py` / `export.py`, use:

- `docs/plans/post_audit_maintainability_wave1.md`

Do not open broader cleanup outside that limited scope.

---

## Failure Modes

1. Mixing local and shared-infra rows in one patch wave
2. Fixing stale docs without fixing the underlying code row
3. Reintroducing deleted compatibility helpers while patching orchestration
4. Claiming closure before the ledger row is actually resolved

---

## Exit Condition

This plan is complete when:

- the local rows above have child implementation waves,
- each wave has explicit acceptance criteria,
- and the remaining shared-infra-blocked rows stay outside `grounded-research`.
