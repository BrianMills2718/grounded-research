# Plan: Documentation Authority Reconciliation

`docs/PLAN.md` remains the canonical repo-level plan. This file covers the
remaining documentation cleanup needed so the active implementation state and
the active plans stop contradicting each other.

**Status:** Completed
**Type:** design
**Priority:** Medium
**Blocked By:** None
**Blocks:** Clean handoff and unambiguous long-term planning

---

## Gap

**Current:** The repo has enough documentation, but authority is split across
surfaces that no longer agree on what is active, implemented, or next.

**Target:** One coherent documentation surface where:

- `CLAUDE.md` defines operating policy
- `docs/PLAN.md` defines the canonical execution plan
- `docs/plans/` reflects actual active/completed work
- `docs/ROADMAP.md` matches the current implementation frontier

**Why:** Planning drift is now a real productivity cost. It creates false
priorities and makes review harder than the code itself.

---

## References Reviewed

- `CLAUDE.md`
- `AGENTS.md`
- `docs/PLAN.md`
- `docs/ROADMAP.md`
- `docs/plans/CLAUDE.md`
- `docs/plans/depth_modes.md`
- `docs/plans/v1_reasoning_quality_execution.md`
- `docs/plans/wave2_enumeration_grounding.md`
- `docs/TECH_DEBT.md`

---

## Files Affected

- `CLAUDE.md` (modify)
- `AGENTS.md` (modify/resync)
- `docs/PLAN.md` (modify)
- `docs/ROADMAP.md` (modify)
- `docs/plans/CLAUDE.md` (modify)
- `docs/plans/depth_modes.md` (modify)
- `docs/TECH_DEBT.md` (modify)

---

## Pre-Made Decisions

1. The active implementation frontier is the post-Wave-2 cleanup surface, not the old runtime-blocked UBI recovery state.
2. `depth_modes.md` is not “planned from scratch”; it is partially implemented
   with deeper follow-on work deferred.
3. `ROADMAP.md` must stop leading with older fasting/search-diversification
   priorities while Wave 2 reliability is the real blocker.
4. `AGENTS.md` must mirror `CLAUDE.md` exactly after the reconciliation pass.

---

## Plan

### Steps

1. Update `CLAUDE.md` to make autonomous continuation requirements explicit.
2. Resync `AGENTS.md` from `CLAUDE.md`.
3. Update `docs/plans/CLAUDE.md` so statuses reflect reality.
4. Update `docs/ROADMAP.md` so the first priorities are:
   - Wave 2 runtime reliability
   - Wave 2 benchmark closure
   - docs authority cleanup
5. Narrow outdated plan statuses and notes in `depth_modes.md` and related docs.

---

## Acceptance Criteria

- [x] `CLAUDE.md` and `AGENTS.md` match exactly
- [x] `docs/plans/CLAUDE.md` reflects actual active/completed plan state
- [x] `docs/ROADMAP.md` matches the real current frontier
- [x] No active doc claims that depth modes are entirely unimplemented

---

## Notes

- Completed 2026-03-26 after the runtime, coverage, and report-calibration
  slices landed and the README/ROADMAP/plan surfaces were updated to reflect
  the calibrated UBI result.
