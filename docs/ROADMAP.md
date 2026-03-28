# Roadmap

**Last updated:** 2026-03-28
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
- 3 independent analyst roles with distinct reasoning frames
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

## Tyler-Native Status

The contract migration wave, benchmark re-anchor, and repo-local prompt-quality
recovery wave are complete. The Tyler runtime is mechanically stable end-to-end,
now beats cached Perplexity on the tracked UBI case, and still trails the saved
dense-dedup anchor slightly.

Current state after the completed recovery wave:

- `output/tyler_literal_parity_ubi_reanchor_v8/` beats cached Perplexity on the
  tracked UBI comparison
- it still trails the saved dense-dedup anchor slightly
- that residual gap is now explicit: the dense-dedup path still packages more
  breadth/context and alternatives than the Tyler-native path

If the remaining blocker is only provider/runtime behavior or frontier-model
availability after this recovery, record it as a shared-infra issue instead of
reopening local contract work.

Current stop line:

- do not reopen repo-local Tyler contract work without a new benchmark-triggered
  grounded-research-specific diagnosis
- treat remaining provider/model/search-stack differences as shared-infra work
  in `llm_client`, `prompt_eval`, or `open_web_retrieval`

Current implementation frontier:

- execute `docs/plans/tyler_canonical_cutover.md`
- treat `docs/plans/legacy_export_surface_deletion.md` as completed
- treat `docs/plans/stage45_projection_deletion.md` as completed
- treat `docs/plans/stage13_runtime_projection_cutover.md` as completed
- treat `docs/plans/isolated_compatibility_surface_deletion.md` as completed
- execute `docs/plans/current_shape_model_surface_deletion.md` as the current
  child wave under that cutover
- remove the remaining current-shape model/helper debt aggressively
- preserve older tuned variants by commit references and eval-time comparison,
  not as co-equal runtime modes

See:

- `docs/plans/tyler_literal_parity_benchmark_reanchor.md`
- `docs/plans/tyler_literal_prompt_quality_recovery.md`
- `docs/TYLER_LITERAL_PARITY_AUDIT.md`

## Next: Preserve Benchmarks And Choose The Next Expansion Gate

The post-Wave-2 cleanup plan, the first depth-continuation wave, and the
sectioned-synthesis export wave are now complete. The repo-local frontier is
again preserving those gains and only opening another expansion wave when a
benchmark points to a clear grounded-research-specific bottleneck.

### Priority 1: Preserve The Current UBI Win On Future Reruns

**Goal:** Keep the recovered UBI result stable on the runtime-safe fixture path.

**Current benchmark anchor:** the 2026-03-26 dense-dedup fixture rerun completed
with `44 raw -> 36 canonical`, `31` cited claims, `0` grounding warnings, and
a saved fair comparison favoring the pipeline `24` vs cached Perplexity `22`.
The fresh 2026-03-27 `thorough` fixture rerun completed cleanly but regressed
against both cached Perplexity and the prior pipeline anchor, so the
dense-dedup fixture remains the canonical UBI benchmark anchor.

**Actions:**
- keep the runtime-safe fixture path as the default benchmark route
- keep the analyst coverage target, staged dedup, and export repair loops in place
- preserve the saved UBI dense-dedup artifacts as the current economics benchmark anchor

**Gate:** Future improved-bundle UBI reruns still complete end-to-end and do not
regress below the current saved dense-dedup result.

### Priority 2: Preserve The Depth-Wave Gain Without Reopening Broad Complexity

**Goal:** Keep the new deep/thorough extraction and multi-round arbitration
surfaces in place without turning this repo back into a generic runtime or
retrieval layer.

**Current depth-wave anchors:**
- `output/depth_wave1_smoke/`: deep collection smoke completed with `5` sources,
  `19` evidence items, `14` LLM-extracted items, and `0` gaps
- `output/sectioned_synthesis_gate_post2/`: thorough rerender completed with
  `11,281` words, `7` section headings, and no placeholder tokens

**Actions:**
- keep `standard` mode on the legacy low-cost extraction path
- keep richer extraction gated to `deep` and `thorough`
- preserve multi-round arbitration as a depth-only behavior
- preserve sectioned synthesis as the `thorough`-mode long-report path
- do not reopen report rendering again unless a saved benchmark shows a new
  export-specific bottleneck

**Gate:** A future deep/thorough benchmark rerun must show either:
- a regression with a clear grounded-research-specific diagnosis, or
- a clear new export bottleneck before opening the next depth wave

Fresh evidence from 2026-03-27:

- `output/ubi_thorough_preservation_wave1/` completed end-to-end
- it produced `66` canonical claims, `42` cited claims, and `0` grounding warnings
- but the fair comparison still favored cached Perplexity and also favored the
  prior dense-dedup pipeline anchor
- the completed evidence did **not** clearly implicate stale-source dominance,
  so recent-first ranking was **not** opened

### Priority 3: Shared-Infra Follow-Up, Not New Repo-Local Complexity

**Goal:** Avoid reopening settled project code when the remaining issues now
live in shared infrastructure or future benchmark expansion.

**Actions:**
- finish any remaining runtime-default improvements in `llm_client`
- continue using `open_web_retrieval` and shared observability rather than
  reintroducing project-local fetch/runtime logic
- keep Tavily/Exa provider-parity work in `open_web_retrieval`, not here
- evaluate Gemini structured-output quality in `llm_client` / `prompt_eval`
  before expanding Gemini's reasoning-critical structured stages
- use `prompt_eval` for future prompt/model comparison work instead of adding
  new ad hoc comparison surfaces here

**Gate:** No new repo-local complexity is added unless a completed benchmark run
shows a clear grounded-research-specific bottleneck.

### Immediate 24h Ownership

The next 24 hours of work should be treated as three explicit buckets:

1. `grounded-research`
   - finish Tyler canonical cutover by deleting non-live compatibility APIs
   - preserve the saved dense-dedup benchmark anchor
   - preserve the completed depth-wave and sectioned-synthesis behavior
2. shared runtime
   - land any remaining `llm_client` durability/query follow-through on `main`
   - keep runtime policy and observability improvements shared, not local
3. shared retrieval / evaluation
   - keep provider-adapter work in `open_web_retrieval`
   - use `prompt_eval` for Gemini structured-output comparison before changing
     execution policy here

### Priority 4: Choose The Next Benchmark Wave Explicitly

There is currently **no active repo-local implementation wave**.

**Candidates for a future explicit wave:**
- recent-first evidence ranking
- another dense, study-heavy benchmark question if the goal is to stress the
  canonicalization/retrieval stack again
- prompt-eval or benchmark work on export quality if longer reports still lose
  on usefulness despite the new sectioned path

**Gate:** Write or refresh the relevant plan doc before implementation. Do not
reopen broad cleanup work without a benchmark-triggered reason.

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
| -1 | Thesis validation | Done — distinct frames and multi-family thesis validation; current primary runtime defaults are the closest available Tyler-role mapping |
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
