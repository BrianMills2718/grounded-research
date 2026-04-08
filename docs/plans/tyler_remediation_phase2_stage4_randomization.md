# Tyler Remediation Phase 2: Stage 4 Randomization

`docs/PLAN.md` remains the canonical repo-level plan. This file is the second
child implementation wave under `tyler_gap_remediation_wave1.md`.

**Status:** Completed
**Type:** implementation
**Priority:** High
**Blocked By:** `docs/plans/tyler_gap_remediation_wave1.md`
**Blocks:** truthful Tyler Stage 4 primacy-bias mitigation

---

## Goal

Patch `S4-ORDER-RANDOMIZATION-001` in the live Stage 4 path.

Tyler requires Analyst A/B/C presentation order to be randomized before each
Stage 4 claim-extraction call so no analyst is systematically advantaged by
prompt order.

---

## Canonical Inputs

- `docs/TYLER_SPEC_GAP_LEDGER.md`
- `docs/plans/tyler_gap_remediation_wave1.md`
- `src/grounded_research/canonicalize.py`
- `tests/test_canonicalize.py`
- Tyler packet under `tyler_response_20260326/`

If this plan and the ledger disagree, trust the ledger.

---

## Scope

### In Scope

1. randomize Stage 3 analysis-object order before each Stage 4 prompt render
2. preserve all analysis content and alias integrity
3. verify the randomized order reaches the prompt
4. verify retries do not silently reuse a fixed order

### Out of Scope

1. Stage 5 randomization
2. Stage 6 synthesis fixes
3. Stage 3 model assignment fixes
4. broad canonicalize refactors beyond the helper boundary needed here

---

## Pre-Made Decisions

1. Randomization is local orchestration behavior and stays in
   `src/grounded_research/canonicalize.py`.
2. Implement it as a small pure helper that returns a shuffled copy of the
   Stage 3 results.
3. Every Stage 4 call means every prompt render:
   - primary call
   - retry call if used
4. Tests should verify prompt input order, not just helper output.
5. Deterministic tests should inject a seeded or monkeypatched shuffle path.

---

## Implementation Sketch

### Step 1: Extract a pure shuffle helper

In `canonicalize.py`:

- add a helper that copies and shuffles the Stage 3 result list
- do not mutate the caller-owned list

### Step 2: Re-render prompt inputs per call

- build Stage 4 prompt messages from a freshly shuffled list for the primary
  call
- rebuild them again for the retry path instead of reusing the original message
  list

### Step 3: Add targeted tests

- helper-level order-preservation check
- canonicalize-level prompt capture check
- retry-path check proving a retry also goes through a shuffle/render boundary

---

## Success Criteria

Pass only if all of the following are true:

1. Stage 4 no longer forwards a fixed analyst order into the prompt
2. The randomized order reaches the live `render_prompt()` call
3. Retry calls also rebuild prompt input from a fresh randomized order
4. Alias/content integrity is preserved after shuffling

---

## Required Tests

| Test / Check | What It Verifies |
|--------------|------------------|
| targeted `tests/test_canonicalize.py` additions | shuffle helper, prompt-input order, retry re-render behavior |
| `./.venv/bin/python -m py_compile` on touched files | runtime syntax integrity |

---

## Failure Modes

1. shuffling a copy that never reaches `render_prompt()`
2. mutating the caller-owned Stage 3 list and creating downstream alias drift
3. randomizing the first call but reusing fixed-order messages on retry

---

## Exit Condition

This wave is complete when:

- `S4-ORDER-RANDOMIZATION-001` is patched locally,
- tests prove the randomized order reaches Stage 4 prompt rendering,
- and the ledger/status surface can truthfully move Phase 2 behind us.

## Outcome

Completed on 2026-04-08.

Implemented:

1. `canonicalize.py` now randomizes Stage 3 analyst presentation order before
   Stage 4 prompt rendering.
2. Retry calls rebuild the Stage 4 prompt from a fresh randomized order instead
   of reusing fixed-order messages.

Verified with:

- `./.venv/bin/python -m pytest tests/test_canonicalize.py -q`
- `./.venv/bin/python -m py_compile src/grounded_research/canonicalize.py tests/test_canonicalize.py`
- `./.venv/bin/python -m pytest tests/test_phase_boundaries.py tests/test_tyler_v1_stage4_adapters.py -q`
