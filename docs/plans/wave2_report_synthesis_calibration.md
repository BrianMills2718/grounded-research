# Plan: Wave 2 Report Synthesis Calibration

`docs/PLAN.md` remains the canonical repo-level plan. This file is the
executable plan for the next quality slice after the coverage-breadth rerun.

**Status:** Completed
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Closing the remaining UBI gap after analyst/claim breadth improved

---

## Gap

The coverage-breadth slice materially improved the upstream analytical state:

- all three analysts now reached the configured claim target on the improved
  UBI bundle
- raw claims increased to 38
- canonical claims increased to 38
- cited claims in the long report increased to 31

But the fair comparison still favored cached Perplexity. The remaining gap now
looks concentrated in the report synthesis layer:

- the report still lost on completeness, conflict/nuance, analytical depth, and
  decision usefulness
- the long report included a symbolic placeholder (`X-Y%`) instead of a real
  estimate or an explicit “cannot estimate”
- the report did not foreground a strong “reconciling apparent contradictions”
  section even though that is exactly where the judge found Perplexity stronger
- the structured report still missed at least one unresolved dispute in its
  disagreement summary, producing a grounding warning

---

## Goal

Make the report layer more decision-useful on dense benchmark questions without
relaxing grounding or switching models.

Specifically:

1. eliminate symbolic placeholders and similar synthesis artifacts
2. force stronger contradiction-reconciliation structure in the long report
3. improve explicit cross-case comparison when many named studies/pilots exist
4. repair structured-report grounding failures instead of only warning on them

---

## Files Likely Affected

- `prompts/long_report.yaml`
- `prompts/synthesis.yaml`
- `src/grounded_research/export.py`
- `tests/test_export.py`
- `tests/test_prompt_templates.py`
- `docs/TECH_DEBT.md`

---

## Pre-Made Decisions

1. Start with prompt and validator/repair changes in export, not another analyst
   or retrieval rewrite.
2. Keep analytical mode, but forbid symbolic placeholders such as `X-Y%`, `TBD`,
   or bracketed pseudo-values.
3. Add one repair pass for the structured report when grounding validation fails.
4. Add one repair pass for the long report only on mechanically detectable
   quality failures, starting with placeholder tokens.
5. Require explicit contradiction-reconciliation and cross-case comparison
   structure in the long report prompt when evidence spans multiple cases.

---

## Plan

1. Strengthen `prompts/long_report.yaml`.
   Add explicit requirements for:
   - reconciling apparent contradictions
   - comparing major named studies/pilots/programs directly
   - never emitting symbolic placeholders; say the estimate is not possible if
     it cannot be supported

2. Strengthen `prompts/synthesis.yaml`.
   Make unresolved disputes and disagreement explanation harder to omit.

3. Add a small structured-report repair loop in `export.py`.
   If `validate_grounding()` returns errors, do one corrective regeneration with
   the explicit validation failures fed back to the model.

4. Add a long-report placeholder validator in `export.py`.
   If the long report contains obvious placeholder artifacts, do one corrective
   regeneration with focused feedback.

5. Re-run the improved UBI benchmark and fair comparison.

---

## Acceptance Criteria

- [x] Structured report no longer emits grounding warnings on the improved UBI gate
- [x] Long report no longer contains symbolic placeholders such as `X-Y%`
- [x] Fair comparison improves over the current post-coverage-breadth result

---

## Notes

- Completed 2026-03-26:
  - structured-report repair loop eliminated the previous unresolved-dispute
    grounding warning
  - long-report repair loop removed symbolic placeholder output
  - calibrated UBI rerun produced 39 canonical claims, 31 cited claims, and 0 warnings
  - fair comparison vs cached Perplexity shifted to favor the pipeline on
    decision usefulness, with implied totals of 24 for the pipeline vs 23 for
    Perplexity in the saved judge output
