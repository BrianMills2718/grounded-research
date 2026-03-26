# Roadmap

**Last updated:** 2026-03-26
**Replaces:** ROADMAP_V2.md (stale)

## Current State

**v0.1.0 shipped.** 47/52 scorecard features implemented. Pipeline now beats
cached Perplexity deep research on the tracked 6-question benchmark set,
including the previously weak UBI question after the 2026-03-26 calibration
passes. Cost: ~$0.06/run (standard),
configurable depth modes (standard/deep/thorough).

**Architecture complete:**
- Question decomposition with validation and retry
- Sub-question-driven search (50 sources, parallel fetch)
- 3 cross-family analysts with distinct reasoning frames
- Claim extraction, dedup, dispute detection with severity calibration
- Fresh evidence arbitration for decision-critical disputes
- Analytical + grounded synthesis modes (configurable)
- LLM source quality scoring
- Evidence sufficiency checking per sub-question
- Conflict-aware compression
- Model fallback chains on all call sites
- User steering for preference/ambiguity disputes
- Evidence-label leakage detection
- Arbitration position shuffling

**What's NOT done:**
- 4 features intentionally skipped (#11 falsification quality, #14 Grok/Reddit,
  #17 echo detection, #43 self-preference guard)
- 1 feature remains cut (#6 complexity assessment; #3 ambiguity and #38
  shuffling were later un-cut and implemented)

## Next: Post-Wave-2 Cleanup And Hardening

The active frontier is no longer recovering the UBI benchmark. That recovery
now succeeded. The next work is tightening authority surfaces, preserving the
new benchmark gains, and cleaning up the remaining non-blocking engineering debt.

### Priority 1: Preserve The UBI Recovery On Future Reruns

**Goal:** Make sure the UBI win survives future reruns and remains diagnosable.

**Actions:**
- keep the runtime-safe fixture path as the default benchmark route
- keep the analyst coverage target and export repair loops in place
- preserve the benchmark artifacts and note the remaining residual weaknesses

**Gate:** Future improved-bundle UBI reruns still complete end-to-end and do not
regress below the current calibrated result.

### Priority 2: Remaining Internal Engineering Debt

**Goal:** Remove remaining non-blocking weaknesses that still show up in review or observability.

**Actions:**
- execute `docs/plans/post_wave2_cleanup_hardening.md`
- improve dense canonicalization on enumeration-heavy runs (`raw == canonical`
  still happens too often even when the benchmark now passes)
- clean up remaining internal prompt/config/schema debt that is already tracked
  in `docs/TECH_DEBT.md`

**Gate:** Remaining debt items are explicit and no longer masquerade as active
benchmark blockers.

### Completed Recently: Documentation Authority Reconciliation

The main authority surfaces have been reconciled to the calibrated UBI result.
The remaining cleanup work is historical-doc demotion and notebook-status
normalization, not another status-story rewrite.

### Deferred: Recent-First Evidence Ranking

CLAUDE.md Principle 4 mandates recent-first evidence prioritization.
Currently implemented only as Brave search freshness filter — evidence
is NOT ranked by recency before analyst consumption. Implement when
evidence quality issues are traced to stale sources dominating.

## Long-Term: Ecosystem Integration

These are blocked on other projects being ready (see ecosystem audit).

### onto-canon Integration

Plan exists: `onto-canon/docs/plans/02_grounded_ingestion_adapter.md`.
Blocked on onto-canon proving at least one real data flow end-to-end.

### Source Reputation DB

Deferred idea: `PROJECTS_DEFERRED/source_reputation_db.md`.
Build a persistent DB of source quality across runs. Each pipeline run
improves the next one's evidence collection.

### Digimon Integration

Depends on onto-canon integration working first. The pipeline is:
`research_v3 → grounded-research → onto-canon → Digimon`.
grounded-research's role is producing the claim ledger that feeds the chain.

## Completed Phases (for reference)

| Phase | What | Status |
|-------|------|--------|
| -1 | Thesis validation | Done — cross-family models, severity calibration |
| 0 | Domain model, contracts, trace | Done |
| 1 | Evidence ingest | Done — Brave + Jina fallback, parallel fetch |
| 2 | Independent analysts | Done — 3 models × 3 frames |
| 3 | Canonicalization | Done — extraction, dedup, disputes |
| 4 | Verification & arbitration | Done — fresh evidence, fail-loud |
| 5 | Export | Done — analytical + grounded modes |
| A | Question decomposition | Done — typed sub-questions, validation |
| B | Source quality | Done — LLM scoring, sufficiency, compression |
| C | Model resilience | Done — fallback chains |
| D | User steering | Done — preference dispute prompts |
| F | Deferred features | Done — 6 of 9 promoted, 3 skipped |
