# Plan: V1 Spec Alignment

**Status:** Planning
**Source:** Tyler's V1 spec (2026_0325_tyler_feedback/) vs current implementation
**Overall compliance:** ~50-60% of V1 spec implemented

## Current Situation

The pipeline's architectural shape matches Tyler's V1 (6-stage flow, cross-family
analysts, claim ledger, dispute detection, arbitration). It wins 5/6 against
Perplexity Deep Research with cheap models. But the implementation details
diverge significantly from Tyler's spec in ways that affect reasoning quality.

Tyler's explicit warning: "If the prompts are shorter or cleaner, that's a red flag.
Your prompts are long for a reason."

## Gap Inventory

### CRITICAL: Changes the pipeline's core reasoning quality

#### G1. Claimify extraction not implemented
**V1 spec:** Stage 4 uses Microsoft's Claimify approach — a dedicated LLM pass
(GPT-5.4) that decomposes analyst outputs into atomic claims via 4 steps:
sentence tokenization → context creation → LLM extraction → disambiguation.
Each claim must be self-contained (comprehensible without the original text).

**Current:** `extract_raw_claims()` in `canonicalize.py` is pure Python that
pulls pre-made claims from `AnalystRun.claims`. No LLM-based atomization,
no disambiguation, no context creation. Analysts produce their own claims.

**Impact:** This is the root cause of the claim precision problem. Analysts
produce abstract claims ("pilot programs show minimal effects") because
they're summarizing, not atomizing. Claimify would produce: "The Finnish
Basic Income Experiment (2017-2018, N=2,000) found no statistically
significant difference in employment between treatment and control groups."

**Recommendation:** Implement Claimify as specified. This is the single
highest-impact change.

**Uncertainty:** The V1 spec assigns GPT-5.4 for this step "for best
structured output reliability." We're using cheap models. Does Claimify
work with gpt-5-nano? Unknown — needs testing.

**Effort:** ~2 hours. New prompt, new function, wire into pipeline.

---

#### G2. Conservative dedup safeguards missing
**V1 spec:** "Do NOT merge claims that differ in scope, time horizon,
threshold, causal direction, or hidden assumptions."

**Current:** `dedup.yaml` says "merge claims that assert the same thing"
and "err on the side of keeping claims separate" but doesn't list the
specific non-merge criteria.

**Impact:** Subtle disagreements get collapsed. The pipeline reports
consensus where there was actually a meaningful difference. This is
invisible — you'd never know claims were lost.

**Recommendation:** Add the 5 specific non-merge criteria to dedup.yaml.

**Effort:** 15 minutes. Prompt change only.

---

#### G3. Evidence labeling hierarchy wrong
**V1 spec:** 4-tier numeric labels ON CLAIMS (not sources):
- vendor_documented = 1.0
- empirically_observed = 0.8
- model_self_characterization = 0.5
- speculative_inference = 0.3

**Current:** We have `quality_tier` on sources (authoritative/reliable/
unknown/unreliable) — a different concept. Tyler's spec labels the
CLAIM's evidence basis, not the source's reputation.

**Impact:** No way to distinguish "this claim is backed by an RCT" from
"this claim is one model's speculation." Both look the same in the ledger.

**Recommendation:** Add `evidence_label` field to Claim model. Assign
during Claimify extraction (G1). Keep source quality scoring too — they
measure different things.

**Uncertainty:** Should this be assigned by the Claimify extraction LLM
or by a separate validation pass? V1 spec assigns it during extraction.

**Effort:** 30 minutes if done with G1. Schema change + prompt addition.

---

#### G4. Prompts are too short
**V1 spec:** PROMPTS.md contains detailed, technique-specific prompts with
named research methods (Claimify, Chain of Evidences, DMAD frame diversity),
specific failure modes to avoid per frame, and explicit safeguards.

**Current:** Our prompts are functional but generic. They say "be specific"
instead of implementing the specific techniques Tyler researched.

**Impact:** Tyler: "A developer using AI coding tools will be tempted to
'just get the pipeline working' and write simpler prompts that produce
valid JSON. The pipeline will run. The output will look professional. But
the reasoning quality — the entire point — will be mediocre."

**Recommendation:** Replace our prompts with Tyler's V1_PROMPTS.md
versions, adapted for our schema. This is the single most important
change per Tyler's explicit guidance.

**Concern:** Tyler's prompts reference specific model behaviors (Claude's
effort parameter, Gemini's thinking tiers, GPT-5.4's constrained
decoding). These may not apply to our cheap models. Need to test whether
the techniques degrade gracefully with smaller models.

**Effort:** ~3 hours to adapt all prompts. Requires careful line-by-line
work, not automated replacement.

---

### HIGH: Affects pipeline correctness

#### G5. Stage summaries not emitted
**V1 spec:** Every stage emits a `StageSummary` with: stage_name, goal,
key_findings, decisions_made, outcome, reasoning. These feed into the
final report's process_summary component.

**Current:** `PhaseTrace` has operational metadata (started_at, succeeded,
llm_calls, output_summary) but no analytical reasoning. No StageSummary
class exists.

**Impact:** The final report can't include a "process summary" showing how
the pipeline reasoned. Trace.json is operational, not analytical.

**Recommendation:** Add StageSummary schema, emit from each stage.

**Effort:** 1 hour. Schema + emission points in engine.py.

---

#### G6. Dispute types don't match spec
**V1 spec:** 5 types: empirical, interpretive, preference_weighted,
spec_ambiguity, other.

**Current:** 4 types: factual_conflict, interpretive_conflict,
preference_conflict, ambiguity. No "other" type.

**Impact:** Type names differ (factual_conflict vs empirical, etc.).
The routing table works but the vocabulary doesn't match Tyler's spec.

**Recommendation:** Rename to match spec. Add "other" type.

**Uncertainty:** Is this just naming or does the routing logic differ?
V1 spec: empirical→verify, interpretive→arbitrate, preference/ambiguity/
other→surface. Current: factual→verify, interpretive→arbitrate,
preference/ambiguity→surface. Functionally equivalent except for naming
and missing "other" route.

**Effort:** 30 minutes. Schema rename + prompt updates.

---

#### G7. Anti-conformity enforcement gaps
**V1 spec:** Three layers:
1. Architectural independence (separate API calls) — DONE
2. Position randomization before arbitration — DONE
3. Position changes require citing: new_evidence, corrected_assumption,
   or resolved_contradiction — PROMPT-LEVEL ONLY

**Current:** Layer 3 exists in the arbitration prompt but isn't validated
in code. The ArbitrationResult requires new_evidence_ids for non-
inconclusive verdicts (ADR-0004), but doesn't validate that the evidence
is relevant to the position change.

**Recommendation:** Add `basis_type` field to claim updates (new_evidence |
corrected_assumption | resolved_contradiction). Add post-arbitration
validator that checks basis_type against the cited evidence.

**Effort:** 1 hour. Schema + validator + prompt update.

---

#### G8. User steering not visible in current review
**V1 spec:** Stage 6a: filter for preference/ambiguity disputes, print to
terminal, collect free-text input, max 2 questions.

**Current:** This IS implemented in engine.py (lines ~152-165) but the
reviewer didn't see it. The implementation checks `sys.stdin.isatty()`
and prompts for preference/ambiguity disputes.

**Status:** IMPLEMENTED but Tyler's reviewer missed it. May need better
documentation or the implementation may not match spec closely enough.

**Action:** Verify implementation matches V1 spec. Document in README.

---

### MEDIUM: Affects completeness but not core reasoning

#### G9. Search APIs differ (Brave vs Tavily+Exa)
**V1 spec:** Tavily (primary) + Exa (secondary, semantic search).

**Current:** Brave Search only.

**Impact:** Different search results, different evidence base. Exa's
semantic search could find relevant results that keyword search misses.

**Recommendation:** This is the search diversification item from ROADMAP.
Implement when other gaps are closed.

**Uncertainty:** Tyler's spec says "Source Strategy (Locked)" for Tavily+Exa.
Does he still want these specific providers, or is Brave acceptable?

**Effort:** 2-3 hours per provider (Tavily has a Python SDK).

---

#### G10. Query variants via LLM not string templates
**V1 spec:** "String templates, not a model call" for query variants.
Append modifiers like "best practices", "lessons learned", "[topic]
vs alternatives" to sub-question text.

**Current:** LLM generates queries per sub-question.

**Impact:** LLM generation adds cost and may not produce the specific
practitioner-signal patterns Tyler specified ("we found that",
"lessons learned from", etc.).

**Recommendation:** Keep LLM generation (it's working) but add Tyler's
specific query patterns to the prompt so the LLM includes them.

**Effort:** 15 minutes. Prompt change.

---

#### G11. Finding objects not used
**V1 spec:** Evidence extraction produces `Finding` objects with
{finding, evidence_label, original_quote} per source.

**Current:** EvidenceItem has content + content_type but no
original_quote preservation or evidence_label.

**Impact:** Original quotes aren't preserved through the pipeline.
Tyler's spec says "preserve original quotes rather than paraphrasing;
paraphrasing introduces harmonization bias."

**Recommendation:** Add `original_quote` field to EvidenceItem.
Implement quote preservation in fetch_page evidence extraction.

**Effort:** 1 hour. Schema + extraction change.

---

#### G12. Report structure incomplete
**V1 spec:** 11 components in 3 tiers:
- Tier A: executive_recommendation, conditions_of_validity,
  decision_relevant_tradeoffs
- Tier B: disagreement_map, preserved_alternatives, key_assumptions,
  confidence_assessment, process_summary
- Tier C: claim_ledger_excerpt, evidence_trail, evidence_gaps

**Current:** FinalReport has: recommendation, alternatives,
disagreement_summary, evidence_gaps, flip_conditions, cited_claim_ids.
Missing: conditions_of_validity (separate from flip_conditions?),
process_summary, confidence_assessment (as structured list).

**Recommendation:** Align FinalReport schema with 11-component spec.

**Effort:** 1 hour. Schema + prompt changes.

---

#### G13. Grounding check and zombie check not implemented
**V1 spec:** Two runtime validation checks:
1. Grounding: regex confirms recommendation cites claims from ledger
2. Zombie: programmatic check that eliminated alternatives aren't
   still present in the recommendation

**Current:** `validate_grounding()` checks claim ID resolution and
evidence linkage. No zombie check.

**Recommendation:** Add zombie check.

**Effort:** 30 minutes. Code-only validation function.

---

### LOW: Naming/config issues

#### G14. Model assignments unclear
**V1 spec:** Explicit model-to-frame mapping:
- GPT-5.4 → step_back_abstraction
- Claude Opus → verification_first
- Gemini 3.1 Pro → structured_decomposition

**Current:** Config lists models and frames in order but doesn't
document the assignment rationale.

**Action:** Document in config.yaml comments or ADR.

---

#### G15. Verification budget too high
**V1 spec:** Max 3 queries per dispute, max 2 rounds total.
**Current:** verification_max_turns: 10 in config.

**Action:** Change config to match spec.

---

## Questions for Tyler

These are the questions that can't be answered from the spec alone:

1. **Claimify with cheap models:** Your spec assigns GPT-5.4 to Stage 4
   "for best structured output reliability." Does Claimify work with
   gpt-5-nano? Or does this technique require frontier models to produce
   atomic, self-contained claims?

2. **Prompts vs results:** Your prompts are designed for specific model
   behaviors (Claude's effort parameter, Gemini's thinking tiers). We're
   using cheap models that may not respond to these techniques the same
   way. Should we: (a) use your prompts verbatim and accept whatever the
   cheap models produce, (b) adapt the techniques for cheaper models, or
   (c) use frontier models for the prompt-critical stages (Stage 3, 4, 5)?

3. **Tavily+Exa vs Brave:** Your spec locks Tavily+Exa. We use Brave. Is
   this a hard requirement or is Brave acceptable? Adding Tavily is easy
   (Python SDK); Exa adds semantic search which keyword search can't do.

4. **Evidence labeling on claims:** Your spec labels claims with evidence
   strength (vendor_documented → speculative_inference). Should this label
   affect arbitration weight, or is it only for the final report?

5. **Win rate vs spec compliance:** The current simpler implementation wins
   5/6 against Perplexity. Some V1 spec features (Claimify, evidence
   labeling, conservative dedup) would improve quality but add complexity
   and cost. Is spec compliance the priority, or is the benchmark result
   sufficient?

## Recommendations

**If spec compliance is the priority:**
Implement in this order (highest impact first):
1. G4 — Replace prompts with Tyler's V1_PROMPTS.md (biggest quality lever)
2. G1 — Implement Claimify extraction (solves claim precision)
3. G2 — Add conservative dedup safeguards (prevents claim collapse)
4. G3 — Add evidence labeling on claims (quality signal)
5. G7 — Harden anti-conformity enforcement (protocol integrity)
6. G5 — Add stage summaries (observability)

Estimated total effort: ~8-10 hours.

**If benchmark results are the priority:**
The current implementation already wins 5/6. Focus on:
1. G1 — Claimify (would likely flip the UBI loss)
2. G2 — Conservative dedup (prevents claim collapse)
3. G4 — Key prompt improvements (not full replacement)

Estimated total effort: ~4 hours.

**My recommendation:** Start with G4 (prompts) and G1 (Claimify). These
are the two changes Tyler cares most about. Test on the UBI question
(our one loss). If those close the gap, the other changes are lower
priority. If they don't, implement G2, G3, G7 in order.
