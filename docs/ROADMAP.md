# Roadmap

**Last updated:** 2026-04-09
**Replaces:** ROADMAP_V2.md (stale)

## Current State

**v0.1.0 shipped.** The live repo is Tyler-native on the local Stage 1-6
runtime path and the three-case frozen-eval gate is satisfied for the current
lane, but the exhaustive Tyler packet audit has now reopened several narrow
local gaps in Stage 2 and Stage 6 plus a Stage 3 packet ambiguity. The
frontier-model variability item remains a separate policy-governed
operational watch.

Current operational reality:

- Tyler-native Stage 1-6 runtime and export/handoff contracts are the live path
- Stage 1 runs without a separate validation stage
- Stage 2 currently uses routed Tavily/Exa search, but the exhaustive audit
  has reopened whether query diversification should be an orchestrator string
  template rather than the current model call
- Stage 2 quality scoring is deterministic authority/freshness/staleness
  scoring, not a generic LLM judge
- Stage 4 and Stage 5 randomization protections are live
- Stage 5 uses Tyler query roles plus structured search controls
- Stage 6 steering, evidence propagation, compaction, and non-dominant
  synthesis-model policy are live
- Gemini strict-schema parity is landed in shared infra on `llm_client/main`
- the exact Tyler frontier model-version row is now closed
- the remaining Tyler watch item is frontier model-output variability / policy
  handling under the explicit threshold

What is intentionally not the current frontier:

- new local runtime families
- reopening compatibility-deletion work
- broad benchmark expansion as a blocking prerequisite

## Tyler-Native Status

The contract migration wave, benchmark re-anchor, and repo-local prompt-quality
recovery wave are complete. The Tyler runtime is mechanically stable end-to-end,
now beats cached Perplexity on the tracked UBI case, and still trails the saved
dense-dedup anchor slightly.

Current state after the completed recovery wave and the April 2026 clause-by-clause audit:

- `output/tyler_literal_parity_ubi_reanchor_v8/` beats cached Perplexity on the
  tracked UBI comparison
- it still trails the saved dense-dedup anchor slightly
- that residual gap is now explicit: the dense-dedup path still packages more
  breadth/context and alternatives than the Tyler-native path

If the remaining blocker is only provider/runtime behavior or frontier-model
availability after this recovery, record it as a shared-infra issue instead of
reopening local contract work.

Current stop line:

- do not reopen repo-local compatibility-deletion work or invent new local
  runtime families
- do reopen repo-local Tyler remediation work when the gap ledger confirms a
  concrete local divergence
- treat remaining provider/model/search-stack differences as shared-infra work
  in `llm_client`, `prompt_eval`, or `open_web_retrieval`

Current implementation frontier:

- treat `docs/plans/tyler_canonical_cutover.md` as completed for repo-local
  runtime debt
- preserve older tuned variants by commit references and eval-time comparison,
  not as co-equal runtime modes
- do not reopen local compatibility deletion without a new benchmark-triggered
  grounded-research-specific diagnosis
- the first two frozen `prompt_eval` Tyler-literal vs calibrated-legacy
  comparisons are now complete
- the next concrete work is:
  - run the exhaustive Tyler packet audit against all four canonical source
    files, not just the previously identified stage lanes
  - use `docs/TYLER_FULL_SPEC_AUDIT_MATRIX.md` to prove every Tyler source
    section has been inventoried and audited
  - continue to drive all real findings into `docs/TYLER_SPEC_GAP_LEDGER.md`
  - keep the Tyler audit-governance layer active so future status claims
    cannot outrun the evidence in the ledger
  - treat the resulting high-severity local divergences as the next
    implementation frontier because the ledger has now confirmed them
  - keep the next remediation order explicit in
    `docs/plans/tyler_gap_remediation_wave1.md`
  - keep the frozen comparison gate satisfied without treating broader eval as
    the current blocker
  - land remaining shared provider/model parity work
  - preserve the new shared Tavily-backed search path as the quality-first default
  - keep the one Tyler-internal Stage 2 prompt/schema ambiguity documented rather than papered over

See:

- `docs/plans/tyler_literal_parity_benchmark_reanchor.md`
- `docs/plans/tyler_literal_prompt_quality_recovery.md`
- `docs/TYLER_LITERAL_PARITY_AUDIT.md`
- `docs/plans/tyler_faithful_execution_remainder.md`
- `docs/plans/tyler_prompt_literalness_wave1.md`
- `docs/TYLER_EXECUTION_STATUS.md`

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
- keep Exa/provider-expansion work in `open_web_retrieval`, not here
- evaluate Gemini structured-output quality in `llm_client` / `prompt_eval`
  before expanding Gemini's reasoning-critical structured stages
- use `prompt_eval` for future prompt/model comparison work instead of adding
  new ad hoc comparison surfaces here

**Gate:** No new repo-local complexity is added unless a completed benchmark run
shows a clear grounded-research-specific bottleneck.

### Immediate 24h Ownership

The next 24 hours of work should be treated as three explicit buckets:

1. `grounded-research`
   - preserve the saved dense-dedup and Tyler-literal benchmark anchors
   - keep active docs aligned with the canonical Tyler gap ledger
   - keep failure-analysis and prevention controls aligned with the active
     audit and remediation state
   - plan and execute the next local remediation waves from verified ledger
     rows only
   - do not add new local runtime branches or legacy fallbacks
2. shared evaluation
   - compare Tyler-literal against calibrated legacy in `prompt_eval`
   - treat prompt/model family comparison as eval-time work, not runtime modes
3. shared runtime / retrieval
   - land any remaining `llm_client` durability/query follow-through on `main`
   - keep provider-adapter and search-stack work in `open_web_retrieval`

Completed wave:

- `docs/plans/tyler_literal_default_eval_wave1.md`
- `docs/notebooks/29_tyler_literal_default_eval_wave1.ipynb`

Wave 1 outcome (historical proof-of-concept):

1. frozen manifest, harness, and saved outputs now exist
2. `prompt_eval` completed the comparison end to end from saved outputs
3. the result favored Tyler-literal over the archived calibrated legacy anchor
   on the tracked UBI case
4. at that point the remaining limit was explicit one-case coverage, not an ambiguous runtime
   choice

Wave 2 outcome:

1. PFAS now exists as a second matched Tyler-vs-legacy frozen case
2. Tyler-literal was again favored over archived calibrated legacy
3. the frozen-eval story is now two-case directional evidence, not one-case evidence
4. this wave closed the proof-of-concept gap at the time it landed

Wave 3 outcome:

1. `llm_swe` now exists as a third matched Tyler-vs-legacy frozen case
2. Tyler-literal was again favored over archived calibrated legacy
3. the frozen-eval story is now three-case directional evidence, not just a
   two-case story
4. the current eval gate is now satisfied for the active implementation lane

Current evaluation policy:

- do not expand the frozen comparison set by default just to chase more breadth
- add new matched cases only when a later implementation wave needs regression
  coverage
- keep archived calibrated legacy behavior as eval-time comparison only
- do not reintroduce alternate runtime modes in `grounded-research`

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
| -1 | Thesis validation | Done — distinct frames and multi-family thesis validation; the live Stage 3 family/role mapping now matches Tyler's intended A/B/C assignment, with only the exact Gemini 3.1 Pro model-version row still open |
| 0 | Domain model, contracts, trace | Done |
| 1 | Evidence ingest | Done — Brave + Jina fallback, parallel fetch |
| 2 | Independent analysts | Done — 3 models × 3 frames |
| 3 | Canonicalization | Done — extraction, dedup, disputes |
| 4 | Verification & arbitration | Done — fresh evidence, fail-loud |
| 5 | Export | Done — analytical + grounded modes |
| A | Question decomposition | Done — typed sub-questions and prompt-level self-check; the separate validation stage was later removed for Tyler parity |
| B | Source quality | Done — deterministic source scoring, sufficiency, compression |
| C | Model resilience | Done — fallback chains |
| D | User steering | Done — preference dispute prompts |
| F | Deferred features | Done — 6 of 9 promoted, 3 skipped |
