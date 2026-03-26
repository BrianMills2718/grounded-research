# Roadmap

**Last updated:** 2026-03-26
**Replaces:** ROADMAP_V2.md (stale)

## Current State

**v0.1.0 shipped.** 47/52 scorecard features implemented. Pipeline beats
Perplexity deep research on 5/6 test questions. Cost: ~$0.06/run (standard),
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
- 3 features cut (#3 ambiguity was un-cut and implemented, #6 complexity
  assessment, #38 shuffling was un-cut and implemented)

## Next: Wave 2 Completion

The active frontier is no longer raw architecture work. It is finishing Wave 2
after the runtime gate passed locally and the remaining UBI-style enumeration
gap became attributable to coverage breadth rather than simple completion.

### Priority 1: Coverage Breadth On Enumeration-Heavy Bundles

**Goal:** Improve the current UBI fair comparison result by getting the analyst
and raw-claim layers to reflect the breadth already present in the evidence bundle.

**Actions:**
- wire `analyst_claim_target` into the real analyst prompt path
- add one corrective retry when rich bundles produce materially under-covered
  analyst outputs
- verify the improved-bundle UBI rerun yields broader analyst/claim coverage

**Gate:** The improved-bundle UBI rerun produces materially broader analyst
outputs and improves the fair comparison against cached Perplexity, or exposes a
smaller next bottleneck from completed evidence.

### Priority 2: Runtime Reliability For Long Benchmark Runs

**Goal:** Keep the now-working runtime gate stable for long benchmark runs.

**Actions:**
- keep run-local `LLM_CLIENT_DB_PATH` and explicit request timeouts as the
  default runtime policy
- confirm future benchmark reruns still complete cleanly under that policy
- push remaining robustness into shared infra only if project-local policy stops
  being sufficient

**Gate:** Improved-bundle benchmark runs continue to complete end-to-end without
shared DB lock failure or indefinite provider wait as the primary blocker.

### Priority 3: Documentation Authority Reconciliation

**Goal:** Make the active planning and status docs agree on what is current.

**Actions:**
- align `docs/plans/CLAUDE.md`, `docs/ROADMAP.md`, and `CLAUDE.md`
- mark depth modes as partially implemented rather than purely planned
- ensure the active plan set reflects the current frontier

**Gate:** No active doc points to a stale “next step” that conflicts with the
actual active implementation wave.

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
