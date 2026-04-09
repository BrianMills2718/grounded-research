# Tyler Systematic Review Wave 2

**Status:** Completed
**Type:** audit plan
**Priority:** High
**Parent plan:** `docs/plans/tyler_faithful_execution_remainder.md`

## Goal

Run one repeatable, clause-by-clause review of the live `grounded-research`
system against Tyler's packet so the remaining work is driven by evidence
rather than memory, prose summaries, or one-off reviews.

This wave exists because the repo now has:

- a canonical gap ledger,
- a truthful current-status surface,
- and a much smaller remaining frontier,

but it does not yet have one compact execution program that says exactly how to
re-review the whole system without drifting back into overclaims.

## Scope

In scope:

- Tyler packet clause inventory used by `grounded-research`
- local code review against Tyler clauses
- behavior verification for routing/order/propagation/model-policy claims
- docs/status review against the ledger
- shared-infra touchpoints that materially affect Tyler compliance in this repo

Out of scope:

- broad new feature work
- benchmark expansion beyond the already-satisfied three-case eval gate
- speculative refactors not needed for review or remediation

## Canonical Inputs

The review is anchored to:

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`
- `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`
- Tyler's four canonical packet files already referenced in the ledger

The compact execution tracker for this wave is:

- `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`

## Pre-Made Decisions

1. The ledger remains the canonical evidence surface for findings.
2. The matrix is the canonical execution tracker for the review itself.
3. Every reviewed clause must end in exactly one outcome:
   - `verified_literal`
   - `verified_extension`
   - `verified_fixed`
   - `local_divergence`
   - `shared_infra_blocked`
   - `stale_doc`
   - `tyler_ambiguity`
4. Structure claims may be closed by static inspection.
5. Behavior claims require runtime evidence:
   - targeted test,
   - trace check,
   - fixture run,
   - or provider/request-body verification.
6. Shared-infra rows are reviewed from the consuming boundary in
   `grounded-research`, then pushed outward only if the gap is proven shared.
7. No doc may claim completion unless the underlying ledger row is already
   closed or explicitly marked extension/ambiguity.

## Review Dimensions

Each clause is reviewed across the minimum applicable dimensions:

1. prompt/spec wording
2. local schema/contract surface
3. orchestration/runtime behavior
4. provider/runtime control surface
5. docs/status truthfulness

## Phases

### Phase 1: Freeze Review Inventory

Deliverables:

- compact matrix with every review lane grouped by stage and surface
- explicit evidence requirement per lane

### Phase 2: Local Structure Review

Deliverables:

- static review of prompts, schemas, config, and code paths
- ledger updates for any newly proven local divergence or verified closure

### Phase 3: Behavior Review

Deliverables:

- runtime verification for ordering, propagation, routing, caps, and control
  surfaces
- explicit evidence artifacts cited in the ledger

### Phase 4: Docs And Status Review

Deliverables:

- all active docs checked against the ledger
- any overclaim or stale summary corrected immediately

### Phase 5: Shared Boundary Review

Deliverables:

- remaining shared rows narrowed to:
  - genuine shared blocker,
  - local consumer misuse,
  - or no remaining issue

### Phase 6: Remediation Output

Deliverables:

- open rows grouped into the next remediation wave(s)
- each wave cites exact `spec_id` rows

## Acceptance Criteria

This wave passes only if:

1. every Tyler-relevant review lane is represented in the matrix,
2. every open ledger row has an explicit evidence-backed owner and next action,
3. every behavior claim reviewed in this wave cites runtime evidence,
4. active docs do not overclaim beyond the ledger,
5. any remaining open items are narrow enough to hand directly to a local or
   shared remediation plan.

## Failure Modes

| Failure mode | Symptom | Required response |
|---|---|---|
| Review drift | findings appear only in conversation | write them to the ledger immediately |
| Static-over-runtime mistake | claim about ordering/routing without runtime proof | add or run the missing behavior check |
| Shared/local confusion | repo blames infra without boundary evidence | prove at consuming boundary first |
| Doc overclaim | status surface says done while ledger says open | fix docs immediately |
| Closure by memory | "I think this is fixed" with no cited artifact | treat as open until verified |

## Verification

Minimum verification for the wave:

1. matrix exists and is wired into active docs
2. at least one review lane per stage maps to an evidence requirement
3. any new finding added during the wave is recorded in the ledger, not just in
   prose
4. docs/index surfaces point to this plan and the matrix

## Todo List

- [x] Phase 1: freeze review inventory
- [x] Phase 2: local structure review
- [x] Phase 3: behavior review
- [x] Phase 4: docs and status review
- [x] Phase 5: shared boundary review
- [x] Phase 6: remediation output

## Outcome Target

When this wave is complete, the repo should have one compact answer to:

- what has been reviewed,
- what evidence supports each claim,
- what is still open,
- and what exact remediation wave comes next.

## Progress Note (2026-04-09)

Completed in this wave so far:

- active doc-truth lane closed
- stale active surfaces corrected:
  - `README.md`
  - `docs/FEATURE_STATUS.md`
  - `docs/ROADMAP.md`
  - `docs/TYLER_EXECUTION_STATUS.md`
  - `docs/TYLER_SHARED_INFRA_OWNERSHIP.md`
  - `docs/plans/tyler_faithful_execution_remainder.md`
- exact Tyler model-version row is now closed:
  - `llm_client` PR #28 merged the shared registry surface
  - `docs/plans/tyler_exact_model_version_switch_wave1.md` completed the
    application config switch and raw-question validation run
- frontier runtime/model-policy lane is now review-complete:
  - the remaining ledger row is explicitly governed by
    `docs/plans/tyler_frontier_model_policy_wave1.md`
  - no additional local or shared runtime defect was proven in this wave
- governance lane is now review-complete:
  - no new process gap surfaced after the exact-model closure
  - the ledger-first controls in `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md` and
    `docs/plans/tyler_audit_governance_wave1.md` held

## Completion Note

This wave is now complete.

The review program ended with:

- all tracked review lanes classified in
  `docs/TYLER_SYSTEMATIC_REVIEW_MATRIX.md`
- exact Tyler Gemini model-version parity closed
- doc-truth and governance lanes reconciled
- one remaining open ledger row, `STATUS-FRONTIER-RUNTIME-001`, which is now a
  narrow policy-governed hold rather than an unreviewed ambiguity
