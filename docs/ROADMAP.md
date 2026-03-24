# Roadmap

**Last updated:** 2026-03-24
**Replaces:** ROADMAP_V2.md (stale)

## Current State

**v0.1.0 shipped.** 42/52 scorecard features implemented. Pipeline beats
Perplexity deep research on 2/3 test questions (sanctions 23-22, PFAS 24-20),
loses on fasting (21-24). Cost: ~$0.06/run.

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

## Next: Quality & Competitive Parity

The remaining gap with Perplexity (-3 on fasting) is not architectural.
It's about: (1) preserving quantitative detail through the pipeline, (2)
citing specific organizational positions, (3) addressing population-specific
cautions. These are prompt tuning problems.

### Priority 1: Close the Fasting Gap

**Goal:** Score ≥ 23/25 on fasting (currently 21).

**Actions:**
- Analyst prompt: "cite specific organizational positions by name (AHA, ADA,
  WHO)" and "address population-specific cautions (pregnancy, elderly,
  disordered eating)"
- Verify quantitative claims fix is working (was blocked by rate limit)
- Re-run fasting comparison

**Gate:** Fair comparison ≥ 23/25 on fasting, no regression on sanctions/PFAS.

### Priority 2: Multi-Question Validation

**Goal:** Confidence the pipeline generalizes beyond the 3 test questions.

**Actions:**
- Run pipeline on 3 new questions from different domains (technology,
  economics, science)
- Compare each against Perplexity deep research
- Track win rate and dimension-level scores

**Gate:** Pipeline wins or ties on ≥ 4/6 total questions.

### Priority 3: Search Diversification

**Goal:** Multiple search providers for evidence diversity.

**Actions:**
- Add Exa (semantic search) alongside Brave (keyword search)
- Or add Tavily (built-in content extraction)
- Compare evidence diversity: same question with 1 provider vs 2

**Gate:** Evidence from 2 providers covers more sub-questions than 1 provider.

### Priority 4: Cost Optimization

**Goal:** Reduce per-run cost below $0.03 without quality regression.

**Actions:**
- Identify which LLM calls can use cheaper models (query generation,
  dedup, compression)
- Profile token usage per phase from observability DB
- Test with gemini-2.5-flash-lite for non-critical calls

**Gate:** Cost ≤ $0.03, no score regression on any test question.

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
