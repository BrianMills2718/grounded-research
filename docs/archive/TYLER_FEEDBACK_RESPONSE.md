# Response to Tyler's Feedback (tyler_response_20260331.md)

**Date:** 2026-03-31
**Status:** Tyler's feedback document is **out of date**. Nearly everything
he flagged has been implemented. This document tracks each item.

## Data Model Gaps — ALL FIXED

| Tyler's concern | Status | Evidence |
|---|---|---|
| EvidenceLabel enum (4-level with weights) | **FIXED** | `tyler_v1_models.py`: 4 values + `.weight` property (1.0/0.8/0.5/0.3) |
| StageSummary model | **FIXED** | `tyler_v1_models.py`: 6 fields including `reasoning` |
| AssumptionSetEntry as canonical artifact | **FIXED** | `tyler_v1_models.py`: first-class model in ClaimExtractionResult |
| ClaimStatus lifecycle (8 values) | **FIXED** | `tyler_v1_models.py`: all 8 (initial, supported, contested, contradicted, insufficient_evidence, verified, refuted, unresolved) |
| DisputeType "other" catch-all | **FIXED** | `tyler_v1_models.py`: 5 types including `other` |
| DisputeStatus enum (4 values) | **FIXED** | `tyler_v1_models.py`: unresolved, resolved, deferred_to_user, logged_only |
| ModelPosition on disputes | **FIXED** | `tyler_v1_models.py`: `model_positions: list[ModelPosition]` on DisputeQueueEntry |
| ExtractionStatistics | **FIXED** | `tyler_v1_models.py`: all 6 fields |
| Supporting/contesting model tracking | **FIXED** | `ClaimLedgerEntry.supporting_models`, `.contesting_models` |

## Output Contract Gaps — ALL FIXED

| Tyler's concern | Status | Evidence |
|---|---|---|
| Structured tradeoffs (Tier A #3) | **FIXED** | `SynthesisReport.decision_relevant_tradeoffs: list[Tradeoff]` with `if_optimize_for` + `then_recommend` |
| Key assumptions (Tier B #6) | **FIXED** | `SynthesisReport.key_assumptions: list[KeyAssumption]` with `if_wrong` |
| Confidence assessment (Tier B #7) | **FIXED** | `SynthesisReport.confidence_assessment: list[ConfidenceAssessment]` |
| Process summary (Tier B #8) | **FIXED** | `SynthesisReport.process_summary: list[StageSummary]` |
| Claim ledger excerpt (Tier C #9) | **FIXED** | `SynthesisReport.claim_ledger_excerpt: list[ClaimLedgerExcerpt]` |
| Evidence trail (Tier C #10) | **FIXED** | `SynthesisReport.evidence_trail: list[EvidenceTrailEntry]` |

## Prompt Gaps

| Tyler's concern | Status | Notes |
|---|---|---|
| SHARED_OUTPUT_PROTOCOL on prompts | **PARTIALLY FIXED** | "Return exactly one JSON object" present in all 7 Tyler prompts. Full named block present in decompose + extract_findings. Analyst, stage4, arbitration, synthesis use equivalent instructions inline rather than the named block. |
| DECISION_PROTOCOL block | **PARTIALLY FIXED** | Present in decompose + extract_findings. Not present as a named block in analyst/stage4/arbitration/synthesis — the rules are enforced individually instead. |
| REASONING_REQUIREMENT block | **FIXED** | Present in decompose + extract_findings. All other prompts produce schemas with `reasoning` field, enforcing it at schema level. |
| Context anchoring at end of prompts | **FIXED** | "Original query repeated" at end of: analyst, stage4, synthesis prompts. Arbitration uses dispute context instead. |
| Evidence labeling hierarchy in prompts | **FIXED** | Present in analyst prompt and arbitration prompt. |
| Dispute-adaptive synthesis rules | **FIXED** | `tyler_v1_synthesis.yaml` has conditional rendering guidance per dispute type. |
| Subordination principle in synthesis | **FIXED** | `tyler_v1_synthesis.yaml` contains "SUBORDINATION PRINCIPLE" and "PRIMARY OBLIGATION" sections. |
| Anti-pattern guidance (6 items) | **FIXED** | `tyler_v1_synthesis.yaml` includes: EVIDENCE LAUNDERING, FALSE CONSENSUS, plus 4 others. |
| Self-check in decompose | **FIXED** | `tyler_v1_decompose.yaml` includes self-check instruction. |
| AVeriTeC-style neutral query framing | **FIXED** | `verify.py` generates neutral + limitations + refutation queries per Tyler spec. |
| Quote preservation (original_quote) | **FIXED** | `Finding.original_quote: Optional[str]` in tyler_v1_models.py. |

### Prompt gap uncertainty

The SHARED_OUTPUT_PROTOCOL and DECISION_PROTOCOL are present as **named blocks**
in 2 of 7 prompts (decompose, extract_findings). The other 5 prompts implement
the same rules but inline rather than as named blocks. **Question for Tyler:**
Is the named-block format required in all prompts, or is inline equivalent
acceptable?

## Runtime Validation Gaps

| Tyler's concern | Status | Notes |
|---|---|---|
| Zombie check | **PARTIALLY IMPLEMENTED** | `PreservedAlternative.supporting_claims` references claim IDs, so the schema supports validation. However, there is no explicit runtime reject-and-retry on zombie detection. The grounding check catches missing source references. |
| Grounding errors non-fatal | **CURRENT BEHAVIOR** | Grounding warnings are logged and reported but do not block report generation. Tyler's spec says "2 of 7 anti-patterns checked at runtime" with grounding + zombie, but is ambiguous on whether they should reject-and-retry or just warn. **Question for Tyler: should grounding failures block output?** |

## Search & Model Gaps — MOSTLY FIXED

| Tyler's concern | Status | Notes |
|---|---|---|
| Tavily + Exa dual-API → Brave only | **FIXED** | Both Tavily (primary) + Exa (secondary) run per query. |
| No Claude models anywhere | **FIXED IN CONFIG** | Default config: Claude Opus 4.6 for Analyst B + arbitration. Not yet validated live (OpenRouter latency issues today). |
| Frontier models → budget models | **FIXED IN CONFIG** | Default config: GPT-5.4, Claude Opus 4.6, Gemini 2.5 Pro. Testing config uses cheap models. |
| Stage 4 fallback: same model | **FIXED** | Default config: `claim_extraction` primary GPT-5.4, fallback Claude Opus 4.6 (cross-family). |

## Design Constraint Gaps — ALL FIXED

| Tyler's concern | Status | Notes |
|---|---|---|
| Constraint #5 fully unimplemented | **FIXED** | EvidenceLabel enum with weights, enforced in prompts and schema. |
| Constraint #10 partially unimplemented | **FIXED** | "Original query repeated" at end of analyst, stage4, synthesis prompts. |
| Constraint #4 partially unimplemented | **FIXED** | `status_at_extraction` field preserves pre-arbitration state. |

## Source Quality Gaps

| Tyler's concern | Status | Notes |
|---|---|---|
| Blended quality_score (authority + freshness) | **PARTIALLY FIXED** | Deterministic URL lookup table (Tyler spec for Stage 2). Freshness decay not implemented — Tyler's spec says "URL lookup table" for quality, freshness is separate. |
| Staleness detection (3 regex checks) | **NOT IMPLEMENTED** | Deprecation keywords, version-in-URL, year-mention checks don't exist. These were not in Tyler's V1 Build Plan or Schemas — may be from an earlier spec version. **Question for Tyler: are these V1 requirements?** |
| Research priority per sub-question | **FIXED** | `SubQuestion.research_priority: str` ("high"/"medium"/"low") in schema. |
| Search guidance per sub-question | **FIXED** | `SubQuestion.search_guidance: str` flows from decomposition to collection. |

## Summary

**Of Tyler's ~35 flagged items:**
- **29 are fully fixed**
- **3 are partially fixed** (named prompt blocks, zombie reject-and-retry, freshness decay)
- **1 is not implemented** (staleness regex checks — unclear if V1)
- **2 need Tyler's input** (grounding fatal vs warning, staleness checks scope)
