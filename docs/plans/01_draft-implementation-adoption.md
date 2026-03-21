# Gap 1: Implementation Adoption Gate

`docs/PLAN.md` remains the canonical repo-level plan. This file is for one
scoped review/planning task.

**Status:** 📋 Planned
**Type:** design
**Priority:** High
**Blocked By:** None
**Blocks:** Adoption of local draft implementation files

---

## Gap

**Current:** The repo now contains a committed end-to-end implementation
(`c57cd2c`) spanning `engine.py`, `config/`, `prompts/`, and
`src/grounded_research/*.py`, but that implementation has not yet been adopted
against the canonical plan.

**Target:** An explicit decision for each major implementation surface:
`accept`, `hold`, or `discard`, with the rationale persisted in docs before the
implementation is treated as accepted project state.

**Why:** Without an adoption gate, committed implementation can silently compete
with the canonical plan and create confusion about what the repo has actually
decided.

---

## References Reviewed

- `CLAUDE.md` - canonical project operating rules
- `docs/PLAN.md` - canonical execution plan
- `docs/CONTRACTS.md` - stage-boundary contracts
- `src/grounded_research/models.py` - canonical schema authority
- `engine.py` - current full-pipeline draft
- `config/config.yaml` - current config draft
- `prompts/analyst.yaml` - current analyst prompt draft
- `scripts/phase_minus1.py` - current thesis-falsification draft

---

## Files Affected

- `docs/PLAN.md` (modify)
- `docs/UNCERTAINTIES.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `docs/plans/01_draft-implementation-adoption.md` (create)

---

## Plan

### Steps

1. Inventory the committed implementation surfaces.
2. Compare each surface against the canonical plan and contracts.
3. Record for each surface whether it should be accepted now, held for later,
   or discarded.
4. Persist the unresolved decisions in `docs/UNCERTAINTIES.md`.
5. Update the canonical plan with the adoption gate and immediate next step.

---

## Required Tests

### Validation Checks

| Check | What It Verifies |
|---|---|
| `python scripts/check_markdown_links.py CLAUDE.md docs docs/plans` | doc links remain valid |
| `python scripts/sync_plan_status.py --check` | plan index stays consistent |
| `python scripts/check_required_reading.py docs/plans/CLAUDE.md --reads-file /tmp/nonexistent_reads_for_check` | governance gate covers numbered plans |

---

## Acceptance Criteria

- [ ] Every visible draft implementation surface has an explicit disposition
- [ ] `docs/PLAN.md` states that local drafts do not change accepted milestone status by themselves
- [ ] Open uncertainties are persisted in a backlog surface
- [ ] Governance checks still pass

---

## Notes

This is a review-and-planning gate, not an implementation milestone. The
existence of commit `c57cd2c` does not by itself settle adoption.
