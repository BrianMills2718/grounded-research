# Tyler Remediation Phase 3: Stage 6 Synthesis Context

`docs/PLAN.md` remains the canonical repo-level plan. This file is the third
child implementation wave under `tyler_gap_remediation_wave1.md`.

**Status:** Planned
**Type:** implementation
**Priority:** High
**Blocked By:** `docs/plans/tyler_gap_remediation_wave1.md`
**Blocks:** truthful Tyler Stage 6 synthesis behavior

---

## Goal

Patch the remaining local Stage 6 divergences in one coordinated wave:

- `S6-EVIDENCE-CONTEXT-001`
- `S6-COMPACTION-001`
- `S6-MODEL-POLICY-001`

This wave is grouped because all three rows affect the exact synthesis input
and call policy used by `generate_tyler_synthesis_report()`.

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `docs/plans/post_audit_maintainability_wave1.md`
- `src/grounded_research/export.py`
- `tests/test_export.py`
- Tyler packet under `tyler_response_20260326/`

If this plan and the ledger disagree, trust the ledger.

---

## Tyler Requirements To Implement

### Evidence context completeness

Stage 6 should include the sources that contributed to dispute resolution,
including Stage 5 targeted sources.

### Context compaction

When synthesis input exceeds ~80K characters:

1. keep original query in full
2. keep decision-critical claims in full
3. keep dispute resolutions in full
4. keep Stage 6a user clarifications in full
5. keep evidence highlights for sources that contributed to disputes
6. keep assumptions
7. compress non-critical claims first
8. compress non-dispute evidence to ID + one-line contribution summary
9. preserve front/back anchoring:
   - original query at start
   - key disputes/evidence at end

### Model policy

Stage 6 must not default to the model that dominated earlier stages.

---

## Pre-Made Decisions

1. This wave may use the limited helper extraction allowed by
   `post_audit_maintainability_wave1.md`.
2. `export.py` may gain small pure helpers for:
   - top-source assembly
   - synthesis-input compaction
   - synthesis-model selection
3. Stage 5 additional sources should be represented directly in Stage 6
   `top_sources`, not only indirectly via bundle source IDs.
4. Compaction should use Tyler's char-count heuristic, not a token counter.
5. Model selection should stay configurable, but the default policy must reject
   a synthesis model that dominated earlier stages when a configured alternate
   is available.
6. If dominance cannot be avoided because no alternate is configured, fail loud
   or document the explicit fallback rather than silently pretending parity.

---

## Implementation Sketch

### Step 1: Extract Stage 6 input helpers

In `export.py`:

- build a pure helper for top-source assembly that merges:
  - bundle sources
  - Stage 5 additional sources
- build a pure helper for compaction and ordering of synthesis inputs
- build a pure helper for synthesis-model selection policy

### Step 2: Patch evidence context

- ensure dispute-resolving Stage 5 sources can appear in `top_sources`
- ensure contribution summaries and resolved-dispute links survive

### Step 3: Patch compaction

- measure the pre-render Stage 6 input size with a char-count heuristic
- apply Tyler's priority-ordered compression only when needed
- preserve front/back anchoring

### Step 4: Patch model policy

- detect earlier-stage dominant models from live state/config
- choose a configured non-dominant synthesis model when available
- keep the chosen policy observable and testable

---

## Success Criteria

Pass only if all of the following are true:

1. Stage 5 additional sources can enter Stage 6 synthesis context directly
2. Stage 6 applies Tyler's ~80K-char compaction policy and priority order
3. Stage 6 no longer defaults to a dominant earlier-stage model when a viable
   configured alternate exists
4. tests verify the live assembly behavior, not just helper existence

---

## Required Tests

| Test / Check | What It Verifies |
|--------------|------------------|
| targeted `tests/test_export.py` additions | Stage 5 source inclusion, compaction policy, model-selection policy |
| `./.venv/bin/python -m py_compile` on touched files | runtime syntax integrity |
| one existing export/phase-boundary subset | no regression in the current Tyler-native export path |

---

## Failure Modes

1. adding Stage 5 sources to helper output but not to the prompt payload
2. compressing the wrong surfaces first and violating Tyler's priority order
3. keeping a dominant synthesis default and only documenting it
4. introducing silent fallback model policy instead of fail-loud behavior

---

## Exit Condition

This wave is complete when:

- the three Stage 6 rows above are patched locally,
- tests prove the live synthesis path now follows Tyler's context and model
  policy requirements,
- and the next local remediation wave can move to Stage 3 or Stage 1/2.
