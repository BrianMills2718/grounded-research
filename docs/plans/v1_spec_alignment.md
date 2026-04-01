# Analysis: V1 Spec Alignment

**Status:** Active analysis
**Source:** Tyler's V1 package in `2026_0325_tyler_feedback/`
**Purpose:** Reconciliation memo. This file identifies where the current repo
differs from Tyler's V1. It is not the executable implementation plan.

## Current Position

The repo's architectural shape is close to Tyler's V1:

- decomposition
- first-party web collection
- cross-family analysts
- claim ledger
- dispute routing
- fresh-evidence arbitration
- grounded export

The main remaining gaps are not "missing pipeline stages." They are
reasoning-quality and contract gaps inside the existing stages.

Two constraints now govern alignment work:

1. Stabilize on cheap development models first.
2. Close prompt/contract/protocol gaps before worrying about production-model
   swaps or search-provider parity.

## What Is Already True In Current Code

These points from earlier reviews are outdated as statements about the current
repo:

- The repo is not upstream-bundle-only. It supports raw question ->
  decomposition -> collection -> adjudication in `engine.py` and `collect.py`.
- Late-stage user steering exists for preference/ambiguity disputes in
  `engine.py`.
- Source quality scoring and evidence sufficiency checks are implemented.

Those issues still matter in documentation and positioning, but they are not
current code gaps.

## Gap Inventory

### Wave 1: Required Before Further Stabilization

#### G1. Prompt layer is thinner than Tyler's researched protocol

**Current:** The repo prompts are functional and schema-friendly, but they do
not yet carry Tyler's full prompt method: explicit frame-specific failure modes,
conservative merge rules, anti-conformity anchoring, and the longer
stage-specific instructions that his V1 treats as part of the reasoning method.

**Why it matters:** Tyler's clearest warning was about prompts being silently
"cleaned up" into generic JSON-producing instructions. That risk is real.

**Decision:** Treat prompt hardening as a first-wave alignment task.

---

#### G2. Claimify-style extraction is not implemented

**Current:** `extract_raw_claims()` in `canonicalize.py` copies claims already
produced by the analysts. There is no dedicated claim-atomization pass over
analyst prose.

**Why it matters:** This is the most plausible root cause of abstract claims and
loss of study-level detail.

**Decision:** Add a dedicated claim-extraction stage after analyst generation
instead of assuming analysts will emit final-quality claims.

---

#### G3. Conservative dedup safeguards are too weak

**Current:** Dedup is one structured grouping call with a lightweight prompt and
1:1 fallback on failure.

**Why it matters:** Over-merge hides real disagreement; under-merge floods the
ledger with duplicates. Tyler's spec is explicit that scope, timeframe,
threshold, causal direction, and hidden assumptions must block merging.

**Decision:** Strengthen the dedup prompt and add code-level validation/retry so
zero-group and obvious bad-group outcomes are exceptional.

---

#### G4. Anti-conformity is still only partly protocol-enforced

**Current:** The code requires some `new_evidence_ids` for non-inconclusive
arbitration outcomes, but it does not carry explicit basis types or validate
that the cited basis justifies the claim update.

**Why it matters:** The system can still look rigorous while permitting
hand-wavy claim revision.

**Decision:** Extend the arbitration/update schema and add post-arbitration
validation.

---

#### G5. Analyst anonymization is not mechanically enforced

**Current:** Analysts are labeled Alpha/Beta/Gamma, but downstream text is not
scrubbed for model self-identification phrases.

**Why it matters:** This is a concrete integrity gap, even if it has not yet
shown up often in practice.

**Decision:** Add a post-analyst scrub/validation step before canonicalization.

### Wave 2: Important, But Not Blocking Stabilization

#### G6. Stage summaries are operational, not analytical

`PhaseTrace.output_summary` exists, but Tyler's richer `StageSummary` idea is
not implemented.

#### G7. Report schema does not fully match Tyler's 3-tier output design

The current `FinalReport` works, but it is less structured than Tyler's target
shape.

#### G8. Grounding validation is stronger than before, but zombie-check style
elimination validation is still absent

This matters for synthesis integrity, but it is downstream of the higher-value
Wave 1 work.

### Wave 3: Spec-Parity And Naming Issues

#### G9. Search-provider parity differs from Tyler's locked Tavily+Exa design

This is a real spec divergence, but not automatically a defect while the repo
is stabilizing on Brave-backed first-party collection.

#### G10. Dispute taxonomy naming differs from Tyler's terms

This is lower value than prompt, extraction, dedup, and protocol integrity.

#### G11. Frontier-model role assignment differs from Tyler's production design

This is intentionally deferred until the cheap-model implementation is stable.

## Committed Recommendation

Do not use this file as the implementation plan.

Use it to drive the first execution wave in this order:

1. Harden the prompt layer
2. Implement dedicated claim extraction
3. Harden dedup safeguards and retry behavior
4. Enforce anti-conformity at the schema/validator layer
5. Add anonymization scrubbing

Provider changes, taxonomy renames, and production-model swaps come later.

## Acceptance Criteria

- [ ] Prompt layer hardened with Tyler's frame-specific failure modes, conservative merge rules, anti-conformity anchoring, and stage-specific instructions (G1)
- [ ] Dedicated claim-extraction stage implemented after analyst generation, separate from analyst-produced claims (G2)
- [ ] Dedup safeguards strengthened: prompt carries scope/timeframe/threshold/causal-direction/hidden-assumption blocking rules, with code-level validation and retry on zero-group or bad-group outcomes (G3)
- [ ] Anti-conformity enforced at schema/validator layer: arbitration/update schema requires explicit basis types, and cited basis is validated against the claim update (G4)
- [ ] Analyst anonymization mechanically enforced: post-analyst scrub/validation step removes model self-identification phrases before canonicalization (G5)
- [ ] All Wave 1 gaps (G1-G5) verified against Tyler's V1 spec in `2026_0325_tyler_feedback/`
- [ ] No regression in existing benchmark results after Wave 1 changes

## Execution Plan

The executable plan for Wave 1 lives in:

- `docs/plans/v1_reasoning_quality_execution.md`

That file pre-makes the implementation order, file targets, tests, and
acceptance criteria.
