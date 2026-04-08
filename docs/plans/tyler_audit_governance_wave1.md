# Tyler Audit Governance Wave 1

`docs/PLAN.md` remains the canonical repo-level plan. This file defines the
governance layer for organizing Tyler findings, documenting prior review
failure modes, and preventing future parity overclaims.

**Status:** Active
**Type:** design
**Priority:** High
**Blocked By:** `docs/TYLER_SPEC_GAP_LEDGER.md`
**Blocks:** Future Tyler review, status, and remediation claims

---

## Goal

Create one explicit operating model for Tyler findings so the repo can:

1. organize findings consistently,
2. document what went wrong in earlier review cycles,
3. prevent future docs or plans from claiming closure without ledger evidence.

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/plans/tyler_spec_gap_audit_wave1.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `docs/TYLER_EXECUTION_STATUS.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`

If this plan and the ledger disagree, trust the ledger.

---

## Scope

### In Scope

1. finding organization rules
2. root-cause analysis for previous Tyler review failures
3. prevention controls for future parity/status claims
4. authority-doc reconciliation rules
5. remediation-wave opening rules

### Out Of Scope

1. patching live code gaps
2. shared-infra implementation work
3. expanding the Tyler clause inventory itself

---

## Pre-Made Decisions

1. The ledger remains the clause-level source of truth.
2. Status docs are summaries, not parallel authorities.
3. Historical docs may remain, but they must defer to the ledger when stale.
4. New remediation waves must cite exact `spec_id` rows.
5. Significant misses should be explained by root cause, not just severity.

---

## Deliverables

1. `docs/TYLER_AUDIT_FAILURE_ANALYSIS.md`
2. `docs/plans/tyler_audit_governance_wave1.md`
3. `docs/notebooks/35_tyler_audit_governance_wave1.ipynb`
4. updated authority surfaces pointing at the governance layer:
   - `docs/PLAN.md`
   - `docs/ROADMAP.md`
   - `docs/plans/CLAUDE.md`
   - `docs/plans/tyler_faithful_execution_remainder.md`

---

## Phases

### Phase 1: Document Prior Failure Modes

Document the concrete reasons earlier Tyler review waves overclaimed closure.

Pass if:

- the repo has one explicit failure-analysis document,
- it distinguishes migration, prompt/schema review, orchestration review,
  shared-boundary review, and status-doc drift.

### Phase 2: Define Finding Intake And Organization Rules

Define the workflow from external finding to ledger row to remediation wave.

Pass if:

- the workflow is explicit,
- it names the required organization views,
- it defines when docs must be reconciled.

### Phase 3: Install Prevention Controls

Define the rules that prevent future parity overclaims.

Pass if:

- closure claims are explicitly gated on ledger evidence,
- behavior claims require behavior checks,
- remediation plans must cite ledger rows.

### Phase 4: Wire Governance Into Authority Docs

Update the canonical planning surfaces so the governance layer is not just an
orphaned note.

Pass if:

- the main plan and roadmap mention the governance layer,
- the plan index lists this wave,
- the faithful-execution remainder plan names governance as part of closure.

---

## Verification

1. notebook JSON parses cleanly
2. updated docs are internally consistent
3. authority docs reference the governance layer correctly

---

## Failure Modes

1. creating a postmortem that is not wired into current planning surfaces
2. duplicating the ledger instead of governing it
3. describing root causes vaguely without operational controls
4. allowing historical docs to keep competing with the new governance layer

---

## Exit Condition

This wave is complete when:

- prior review failure modes are documented,
- the Tyler finding workflow is explicit,
- prevention controls are installed in current docs,
- and future remediation/status work has one clear governance path.
