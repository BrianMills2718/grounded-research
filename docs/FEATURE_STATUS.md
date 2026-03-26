# Feature Status: v1 Scorecard vs Current Implementation

**Source:** `v1_Pruning_Scorecard.xlsx`
**Assessed:** 2026-03-26

**Scope note:** This tracks the original pruning scorecard (52 features).
Tyler's V1 spec has additional requirements not in the scorecard — see
`docs/plans/v1_spec_alignment.md` for the gap analysis. A feature marked
DONE here may only partially satisfy the richer V1 contract.

## Legend

- **DONE**: Implemented and verified
- **SKIP**: Intentionally left unimplemented after review
- **CUT**: Marked CUT in scorecard

---

## STAGE 1 — INTAKE & DECOMPOSITION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 1 | Restate query as precise core question | KEEP | **DONE** | `QuestionDecomposition.core_question` reformulates via LLM. |
| 2 | Break into 2-6 typed sub-questions | KEEP | **DONE** | `SubQuestion` with type (factual/causal/comparative/evaluative/scope) + falsification target. ADR-0006. |
| 3 | Identify ambiguous terms & assign definitions | CUT | **DONE** | `AmbiguousTerm` schema in decomposition. Passed through to analysts. Originally cut, later implemented. |
| 4 | Map optimization axes & tradeoffs | KEEP | **DONE** | `QuestionDecomposition.optimization_axes` (2-4 key tradeoffs). Passed to synthesis as organizing framework. |
| 5 | Build research plan with falsification targets | SIMPLIFY | **DONE** | `QuestionDecomposition.research_plan` + per-sub-question `falsification_target`. Drives counterfactual search queries. |
| 6 | Assess complexity level | CUT | CUT | — |
| 7 | Emit stage summary for final report | KEEP | **DONE** | `PhaseTrace` with `output_summary` per phase. |

## STAGE 1v — DECOMPOSITION VALIDATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 8 | Check coverage of decomposition | DEFER | **DONE** | `DecompositionValidation.coverage_ok` + `coverage_gaps` in validation pass. |
| 9 | Flag directional bias | DEFER | **DONE** | `DecompositionValidation.bias_flags` in validation pass. |
| 10 | Check granularity | DEFER | **DONE** | `DecompositionValidation.granularity_issues` in validation pass. |
| 11 | Assess falsification target quality | DEFER | SKIP | Intentionally skipped as low-value meta-validation. |
| 12 | Issue verdict (proceed/caveats/revise) | DEFER | **DONE** | `decompose_with_validation()` retries once on `revise`. |

## STAGE 2 — BROAD RETRIEVAL & EVIDENCE NORMALIZATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 13 | Generate 3-5 query variants per sub-question | KEEP | **DONE** | `generate_search_queries()` creates 15 diverse queries via LLM. Not per-sub-question (no sub-questions exist yet) but per-question with diversity prompting. |
| 14 | Optional Grok/Reddit real-time scan | DEFER | SKIP | Separate search-provider integration, not treated as a core pipeline feature. |
| 15 | Apply source quality scoring | KEEP | **DONE** | `source_quality.py`: LLM batch scoring (authoritative/reliable/unknown/unreliable). Per Brian's critique: LLM, not URL lookup. |
| 16 | Extract atomic findings with evidence tier labels | KEEP | **DONE** | `fetch_page()` extracts key_section + notes per source. `EvidenceItem` has content_type and extraction_method. No explicit "tier labels" on findings. |
| 17 | Echo detection across sources | DEFER | SKIP | Intentionally skipped; judged not worth building in v1. |
| 18 | Conflict-aware compression | SIMPLIFY | **DONE** | `compress.py`: priority-based compression preserving authoritative sources, sub-question coverage, and diversity. |
| 19 | Check evidence sufficiency | KEEP | **DONE** | Per-sub-question coverage check: flags sub-questions with < 2 evidence items as gaps. `EvidenceItem.sub_question_id` tracks origin. |
| 20 | Enforce search budget & diminishing-returns cutoff | SIMPLIFY | **DONE** | Fixed budget: `num_queries` and `max_sources` in config. No diminishing-returns logic. |

## STAGE 3 — INDEPENDENT CANDIDATE GENERATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 21 | Run 3 models in parallel with reasoning frames | KEEP | **DONE** | `run_analysts()` with cross-family models + distinct frames. Async parallel. |
| 22 | Require bottom-line recommendation | KEEP | **DONE** | `AnalystRun.recommendations` is a required field in prompt output. |
| 23 | Require falsifiable claims with evidence references | KEEP | **DONE** | `RawClaim.evidence_ids` required. Hallucinated IDs stripped at extraction. |
| 24 | Require explicit assumptions | KEEP | **DONE** | `AnalystRun.assumptions` is a schema field. |
| 25 | Force counter-argument against own recommendation | SIMPLIFY | **DONE** | `AnalystRun.counterarguments` has `min_length=1` — schema enforces at least one counterargument. |
| 26 | Anonymize analysts & apply anti-conformity | KEEP | **DONE** | Labels Alpha/Beta/Gamma. Analysts don't see each other's outputs (by construction). |

## STAGE 4 — CLAIM EXTRACTION & DISPUTE LOCALIZATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 27 | Decompose analyses into atomic claims | KEEP | **DONE** | `extract_raw_claims()` pulls claims from analyst runs. |
| 28 | Deduplicate claims across models | KEEP | **DONE** | `deduplicate_claims()` via LLM grouping. |
| 29 | Assign global IDs & carry forward evidence labels | KEEP | **DONE** | C- prefix IDs, evidence_ids propagated through dedup. |
| 30 | Evidence-label leakage check | DEFER | **DONE** | URL regex scan on analyst outputs emits `PipelineWarning` on leakage. |
| 31 | Identify cross-model conflicts & classify dispute type | KEEP | **DONE** | `detect_disputes()` with 4 dispute types. |
| 32 | Assess decision-criticality per dispute | KEEP | **DONE** | Severity classification with schema-level guidance. Fixed in this session — was defaulting to "notable" for everything. |
| 33 | Compute resolution routing deterministically | KEEP | **DONE** | `DISPUTE_ROUTING` code-owned table. |

## STAGE 5 — TARGETED VERIFICATION & ARBITRATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 34 | Generate counterfactual queries per disputed claim | KEEP | **DONE** | `generate_verification_queries()` produces search queries for disputed claims. |
| 35 | Search for both supporting & disconfirming evidence | KEEP | **DONE** | Fresh evidence fetched via Brave Search during arbitration. |
| 36 | Schema-driven single-turn critique per dispute | KEEP | **DONE** | `arbitrate_dispute()` with structured ArbitrationResult. |
| 37 | Update claim statuses in ledger | KEEP | **DONE** | `ArbitrationResult.claim_updates` applied to ledger. |
| 38 | Shuffle analyst positions to prevent primacy bias | CUT | **DONE** | `verify.py` shuffles claim order with fixed seed per dispute before arbitration. |
| 39 | Enforce budget controls | SIMPLIFY | **DONE** | `max_disputes`, `max_turns` in config. No novelty detection. |

## STAGE 6a — USER-STEERING INTERRUPT

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 40 | Check for unresolved preference/ambiguity disputes | KEEP | **DONE** | Filters preference/ambiguity disputes after classification. |
| 41 | Formulate structured questions with defaults | SIMPLIFY | **DONE** | TTY prompt with max 2 questions. Auto-skip in non-interactive. User guidance recorded in dispute.resolution_summary. |

## STAGE 6b — SYNTHESIS & FINAL REPORT

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 42 | Context compaction | SIMPLIFY | **DONE** | `compress.py` reduces evidence to threshold. Evidence truncated to 400 chars in long_report prompt. |
| 43 | Self-preference bias guard | DEFER | SKIP | Tested with two judge models (Gemini + GPT-5-nano); no self-preference detected. |
| 44 | Adapt synthesis by dispute resolution type | KEEP | **DONE** | `synthesis_mode` config: "analytical" (inferences beyond sources, marked) vs "grounded" (ledger-only). Disputes handled differently by mode. |
| 45 | Tier A: Executive recommendation & tradeoffs | KEEP | **DONE** | `FinalReport.recommendation` + `alternatives`. Long report has verdict + alternatives sections. |
| 46 | Tier B: Disagreement map, alternatives, confidence | KEEP | **DONE** | `FinalReport.disagreement_summary`, `alternatives`, confidence as enum. |
| 47 | Tier C: Claim ledger, evidence trail, gaps | KEEP | **DONE** | `summary.md` includes full cited claims. `trace.json` has complete ledger. |
| 48 | Anti-pattern validation checks | SIMPLIFY | **DONE** | `validate_grounding()` checks claim ID resolution and evidence linkage. Hallucinated IDs stripped. |
| 49 | Generate trace file with full observability | KEEP | **DONE** | `trace.json` = full `PipelineState`. |

## CROSS-CUTTING — FALLBACK & DEGRADATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 50 | Per-stage model fallback chains | SIMPLIFY | **DONE** | `model_fallbacks` config + `get_fallback_models()`. All 10 LLM call sites pass `fallback_models` kwarg to llm_client. |
| 51 | Minimum-model thresholds & abort conditions | KEEP | **DONE** | `analyst_min_successful: 2` in config. Pipeline aborts if fewer than 2 analysts succeed. |
| 52 | Partial trace output on abort | KEEP | **DONE** | Exception handler writes trace.json with partial state. |

---

## Summary

| Status | Count | Items |
|--------|-------|-------|
| **DONE** | 47 | All KEEP/SIMPLIFY features, plus promoted DEFER items #8, #9, #10, #12, #30 and previously cut items #3, #38 |
| SKIP | 4 | #11, #14, #17, #43 |
| **CUT** | 1 | #6 |

**47/52 features implemented. 4 intentionally skipped. 1 cut.**

*Updated 2026-03-24 from the current spreadsheet, not from stale prose notes.*

## Intentionally Skipped Features

| # | Feature | Why skipped |
|---|---------|-------------|
| 11 | Falsification target quality validation | Low value — targets exist, quality validation is meta |
| 14 | Grok/Reddit real-time scan | Separate search provider, not pipeline feature |
| 17 | Echo detection across sources | Brian: "I wouldn't even try this" |
| 43 | Self-preference bias guard | Tested with 2 judges, no bias detected |
