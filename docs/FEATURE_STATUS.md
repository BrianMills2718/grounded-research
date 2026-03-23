# Feature Status: v1 Scorecard vs Current Implementation

**Source:** `v1_Pruning_Scorecard.xlsx`
**Assessed:** 2026-03-23

## Legend

- **DONE**: Implemented and verified
- **PARTIAL**: Partially implemented or simplified beyond original spec
- **NOT STARTED**: In the scorecard as KEEP/SIMPLIFY but not yet built
- **DEFERRED**: Marked DEFER in scorecard
- **CUT**: Marked CUT in scorecard

---

## STAGE 1 — INTAKE & DECOMPOSITION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 1 | Restate query as precise core question | KEEP | **DONE** | `QuestionDecomposition.core_question` reformulates via LLM. |
| 2 | Break into 2-6 typed sub-questions | KEEP | **DONE** | `SubQuestion` with type (factual/causal/comparative/evaluative/scope) + falsification target. ADR-0006. |
| 3 | Identify ambiguous terms & assign definitions | CUT | CUT | — |
| 4 | Map optimization axes & tradeoffs | KEEP | **DONE** | `QuestionDecomposition.optimization_axes` (2-4 key tradeoffs). Passed to synthesis as organizing framework. |
| 5 | Build research plan with falsification targets | SIMPLIFY | **DONE** | `QuestionDecomposition.research_plan` + per-sub-question `falsification_target`. Drives counterfactual search queries. |
| 6 | Assess complexity level | CUT | CUT | — |
| 7 | Emit stage summary for final report | KEEP | **DONE** | `PhaseTrace` with `output_summary` per phase. |

## STAGE 1v — DECOMPOSITION VALIDATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 8 | Check coverage of decomposition | DEFER | DEFERRED | — |
| 9 | Flag directional bias | DEFER | DEFERRED | — |
| 10 | Check granularity | DEFER | DEFERRED | — |
| 11 | Assess falsification target quality | DEFER | DEFERRED | — |
| 12 | Issue verdict (proceed/caveats/revise) | DEFER | DEFERRED | — |

## STAGE 2 — BROAD RETRIEVAL & EVIDENCE NORMALIZATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 13 | Generate 3-5 query variants per sub-question | KEEP | **DONE** | `generate_search_queries()` creates 15 diverse queries via LLM. Not per-sub-question (no sub-questions exist yet) but per-question with diversity prompting. |
| 14 | Optional Grok/Reddit real-time scan | DEFER | DEFERRED | — |
| 15 | Apply source quality scoring | KEEP | **PARTIAL** | All sources default to `quality_tier="reliable"`. No LLM or domain-based quality scoring. Scorecard debate: Brian wants LLM scoring, not hardcoded URL lookup. |
| 16 | Extract atomic findings with evidence tier labels | KEEP | **DONE** | `fetch_page()` extracts key_section + notes per source. `EvidenceItem` has content_type and extraction_method. No explicit "tier labels" on findings. |
| 17 | Echo detection across sources | DEFER | DEFERRED | — |
| 18 | Conflict-aware compression | SIMPLIFY | **NOT STARTED** | No compression step. Full evidence passed to analysts. Conflicts detected later in Stage 4. |
| 19 | Check evidence sufficiency | KEEP | **PARTIAL** | `EvidenceBundle.gaps` captures fetch failures. No per-sub-question coverage check (no sub-questions). Pipeline continues with whatever evidence it has. |
| 20 | Enforce search budget & diminishing-returns cutoff | SIMPLIFY | **DONE** | Fixed budget: `num_queries` and `max_sources` in config. No diminishing-returns logic. |

## STAGE 3 — INDEPENDENT CANDIDATE GENERATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 21 | Run 3 models in parallel with reasoning frames | KEEP | **DONE** | `run_analysts()` with cross-family models + distinct frames. Async parallel. |
| 22 | Require bottom-line recommendation | KEEP | **DONE** | `AnalystRun.recommendations` is a required field in prompt output. |
| 23 | Require falsifiable claims with evidence references | KEEP | **DONE** | `RawClaim.evidence_ids` required. Hallucinated IDs stripped at extraction. |
| 24 | Require explicit assumptions | KEEP | **DONE** | `AnalystRun.assumptions` is a schema field. |
| 25 | Force counter-argument against own recommendation | SIMPLIFY | **PARTIAL** | Analyst prompt asks for counter-arguments. Not a hard schema requirement — analysts sometimes skip it. |
| 26 | Anonymize analysts & apply anti-conformity | KEEP | **DONE** | Labels Alpha/Beta/Gamma. Analysts don't see each other's outputs (by construction). |

## STAGE 4 — CLAIM EXTRACTION & DISPUTE LOCALIZATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 27 | Decompose analyses into atomic claims | KEEP | **DONE** | `extract_raw_claims()` pulls claims from analyst runs. |
| 28 | Deduplicate claims across models | KEEP | **DONE** | `deduplicate_claims()` via LLM grouping. |
| 29 | Assign global IDs & carry forward evidence labels | KEEP | **DONE** | C- prefix IDs, evidence_ids propagated through dedup. |
| 30 | Evidence-label leakage check | DEFER | DEFERRED | — |
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
| 38 | Shuffle analyst positions to prevent primacy bias | CUT | CUT | — |
| 39 | Enforce budget controls | SIMPLIFY | **DONE** | `max_disputes`, `max_turns` in config. No novelty detection. |

## STAGE 6a — USER-STEERING INTERRUPT

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 40 | Check for unresolved preference/ambiguity disputes | KEEP | **NOT STARTED** | No user-steering loop. Pipeline runs to completion. Unresolved disputes surface in report. |
| 41 | Formulate structured questions with defaults | SIMPLIFY | **NOT STARTED** | No interactive user input during pipeline run. |

## STAGE 6b — SYNTHESIS & FINAL REPORT

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 42 | Context compaction | SIMPLIFY | **PARTIAL** | Evidence capped at 30 items in synthesis prompt. No token-counting or priority truncation. |
| 43 | Self-preference bias guard | DEFER | DEFERRED | Tested with two judge models (Gemini + GPT-5-nano) — no self-preference detected. |
| 44 | Adapt synthesis by dispute resolution type | KEEP | **DONE** | `synthesis_mode` config: "analytical" (inferences beyond sources, marked) vs "grounded" (ledger-only). Disputes handled differently by mode. |
| 45 | Tier A: Executive recommendation & tradeoffs | KEEP | **DONE** | `FinalReport.recommendation` + `alternatives`. Long report has verdict + alternatives sections. |
| 46 | Tier B: Disagreement map, alternatives, confidence | KEEP | **DONE** | `FinalReport.disagreement_summary`, `alternatives`, confidence as enum. |
| 47 | Tier C: Claim ledger, evidence trail, gaps | KEEP | **DONE** | `summary.md` includes full cited claims. `trace.json` has complete ledger. |
| 48 | Anti-pattern validation checks | SIMPLIFY | **DONE** | `validate_grounding()` checks claim ID resolution and evidence linkage. Hallucinated IDs stripped. |
| 49 | Generate trace file with full observability | KEEP | **DONE** | `trace.json` = full `PipelineState`. |

## CROSS-CUTTING — FALLBACK & DEGRADATION

| # | Feature | Verdict | Status | Notes |
|---|---------|---------|--------|-------|
| 50 | Per-stage model fallback chains | SIMPLIFY | **NOT STARTED** | No fallback chains. Single model per stage. llm_client has retry logic but no model fallback. |
| 51 | Minimum-model thresholds & abort conditions | KEEP | **DONE** | `analyst_min_successful: 2` in config. Pipeline aborts if fewer than 2 analysts succeed. |
| 52 | Partial trace output on abort | KEEP | **DONE** | Exception handler writes trace.json with partial state. |

---

## Summary

| Status | Count | Items |
|--------|-------|-------|
| **DONE** | 27 | #1, 2, 4, 5, 7, 13, 16, 20-24, 26-29, 31-37, 39, 44-49, 51-52 |
| **PARTIAL** | 3 | #15, 25, 42 |
| **NOT STARTED** (KEEP/SIMPLIFY) | 4 | #18, 19, 40-41, 50 |
| **DEFERRED** | 9 | #8-12, 14, 17, 30, 43 |
| **CUT** | 3 | #3, 6, 38 |

**27/34 KEEP/SIMPLIFY features implemented. 4 not started. 3 partially done.**

*Updated 2026-03-23: Phase A (decomposition) completed #1, #2, #4, #5. Analytical synthesis mode completed #44.*

## Highest-Impact Remaining Features

| # | Feature | Impact | Phase | Why it matters |
|---|---------|--------|-------|---------------|
| 15 | Source quality scoring (LLM-based) | 3 | B | All sources default to "reliable". LLM scoring would help synthesis weight authoritative sources. |
| 18 | Conflict-aware compression | 3 | B | 96 evidence items in context. Smart compression preserving conflicts would help. |
| 19 | Per-sub-question evidence sufficiency | 3 | B | Flag sub-questions with < 2 sources. |
| 40-41 | User-steering interrupt | 3 | D | Preference disputes surface in report but user can't resolve them mid-run. |
| 50 | Model fallback chains | 3 | C | Single model failure = stage failure. |
