# Plan: Wave 2 Coverage Breadth on Enumeration-Heavy Bundles

`docs/PLAN.md` remains the canonical repo-level plan. This file is the
executable implementation plan for the next quality slice after the runtime
reliability gate passed on the UBI benchmark.

**Status:** Completed
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Closing the remaining UBI gap vs Perplexity on dense, study-heavy questions

---

## Gap

**Current:** The improved UBI bundle now completes end-to-end under the safer
runtime policy, but the finished report still loses the fair comparison against
cached Perplexity. The runtime blocker is no longer the main issue.

The completed runtime-gate artifacts show the remaining weakness more clearly:

- the improved bundle contains 50 sources and 106 evidence items
- evidence already includes many named pilots/studies/programs
- the completed ledger has only 20 canonical claims
- the report uses the available claim ledger, so the bottleneck is not
  primarily export formatting
- the report and ledger over-index a few cases (especially Alaska) and under-
  cover other programs present in the evidence bundle

**Target:** Improve claim-set breadth and coverage discipline on
enumeration-heavy questions without switching away from the cheap-model
development stack.

**Why:** The current remaining loss appears to happen before export. If the
analyst layer and Claimify stage fail to surface enough distinct, named,
evidence-backed cases, the final report cannot recover that missing breadth.

---

## References Reviewed

- `CLAUDE.md` - autonomy rules, plan depth, and verification requirements
- `docs/plans/wave2_enumeration_grounding.md` - active Wave 2 quality-recovery context
- `docs/plans/wave2_runtime_reliability.md` - now-passed runtime gate
- `docs/TECH_DEBT.md` - current benchmark findings and remaining quality risks
- `config/config.yaml` - current depth/runtime policy surface
- `src/grounded_research/config.py` - depth profile accessors
- `src/grounded_research/analysts.py` - analyst prompt rendering and call flow
- `src/grounded_research/models.py` - `AnalystRun` / `RawClaim` structured contract
- `prompts/analyst.yaml` - analyst reasoning instructions
- `prompts/claimify.yaml` - raw-claim extraction instructions
- `output/ubi_wave2_prefetch_collection/collected_bundle.json` - improved UBI evidence bundle
- `output/ubi_wave2_runtime_gate/trace.json` - completed runtime-gate trace
- `output/ubi_wave2_runtime_gate/report.md` - completed long report
- `output/fair_ubi_wave2_runtime_gate_vs_ubi_perplexity.md` - latest fair comparison

---

## Files Likely Affected

- `config/config.yaml` (modify)
- `src/grounded_research/config.py` (modify)
- `src/grounded_research/analysts.py` (modify)
- `prompts/analyst.yaml` (modify)
- `prompts/claimify.yaml` (modify, if needed)
- `tests/test_analysts.py` (create)
- `tests/test_prompt_templates.py` (modify)
- `docs/TECH_DEBT.md` (modify)
- `docs/COMPETITIVE_ANALYSIS.md` (modify if benchmark result changes materially)

---

## Pre-Made Decisions

1. Start at the analyst layer, not export. The report is already using almost
   the entire available claim ledger.
2. Use the existing depth-profile `analyst_claim_target` surface instead of
   inventing a second claim-count policy.
3. Coverage breadth means distinct named studies/pilots/programs should remain
   visible when the evidence bundle actually contains them.
4. The first intervention is one under-coverage retry with stronger guidance,
   not a multi-pass planner or a new post-hoc summarizer.
5. Retry policy must be config-driven and mechanically checkable.
6. Do not relax grounding rules to inflate breadth. Missing breadth must be
   fixed by better evidence-backed claims, not by weaker synthesis.

---

## Plan

### Steps

1. Add a small analysis-coverage policy section to config.
   Include:
   - whether analyst under-coverage retry is enabled
   - the minimum evidence-bundle size that justifies a retry
   - the minimum ratio of `analyst_claim_target` required before retrying

2. Wire `analyst_claim_target` into the analyst prompt.
   The prompt should explicitly require approximately that many distinct,
   evidence-backed descriptive claims when the evidence supports it.

3. Strengthen analyst instructions for enumeration-heavy questions.
   Specifically:
   - when multiple named pilots/studies/programs are present, cover the major
     ones across the claim set
   - do not let one prominent case crowd out the others
   - preserve named-program specificity rather than collapsing into generic
     “pilots show” language

4. Add a single under-coverage retry in `run_analyst()`.
   If a rich bundle yields materially fewer claims than the configured target,
   re-run the same analyst once with corrective feedback about breadth and
   distinct named-case coverage.

5. Add focused tests for:
   - prompt rendering includes the claim target
   - under-coverage detection fires only on rich bundles
   - retry happens once and only when policy conditions are met
   - retry result replaces the under-covered first result

6. Re-run the improved UBI bundle under the runtime-safe path and compare
   against cached Perplexity again.

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Prompt asks for more claims but models still return thin outputs | analyst runs still produce far fewer claims than target on rich bundles | add a single corrective retry before adding more structure |
| Retry increases count by producing low-quality or repetitive claims | claim count rises but many claims duplicate one case or lose specificity | tighten retry instructions around distinct named programs/studies and inspect raw statements |
| Breadth improves by weakening grounding | more claims appear but evidence quality or evidence linkage degrades | reject the change and keep grounding rules strict |
| Analyst coverage improves but the report still loses on completeness | runtime-gate rerun shows broader ledger but no fair-score improvement | inspect Claimify/report synthesis next instead of reworking retrieval again |

---

## Required Tests

### New Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_analysts.py` | `test_run_analyst_retries_when_rich_bundle_is_under_target` | rich bundles trigger one corrective retry when claim count is too low |
| `tests/test_analysts.py` | `test_run_analyst_skips_retry_for_sparse_bundle` | sparse bundles do not retry just because claim count is low |
| `tests/test_analysts.py` | `test_run_analyst_uses_retry_result` | second result replaces the under-covered first result |

### Existing Tests

| Test Pattern | Why |
|--------------|-----|
| `tests/test_prompt_templates.py` | prompt rendering stays valid and includes the new coverage variables |
| `tests/test_phase_boundaries.py` | analyst/ledger/export phase contracts remain stable |

---

## Acceptance Criteria

- [x] `analyst_claim_target` is actually used by runtime prompt generation
- [x] Rich-bundle under-coverage triggers one corrective analyst retry
- [x] Sparse bundles do not retry unnecessarily
- [x] Improved-bundle UBI rerun produces materially broader analyst outputs than the current runtime-gate run
- [x] Fair comparison vs cached Perplexity improves or the next narrower bottleneck is made explicit from completed evidence

---

## Notes

- This plan assumes the runtime reliability gate is already passed locally for
  the improved UBI bundle. If that regresses, fix runtime first rather than
  blaming coverage prompts.
- The current UBI runtime-gate report already cites all 20 canonical claims.
  That is why this slice starts before export.
- Completed 2026-03-26:
  - all three analysts reached the standard-depth target of 8 claims on the
    improved UBI bundle
  - the improved rerun produced 38 canonical claims and 31 cited claims in the
    long report
  - the fair comparison still exposed a narrower remaining bottleneck in report
    synthesis, which moved the next slice to export calibration instead of
    another analyst-layer rewrite
