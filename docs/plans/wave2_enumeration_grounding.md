# Plan: Wave 2 Enumeration and Grounding Recovery

**Status:** In progress
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Reliable performance on enumeration-heavy questions such as UBI

---

## Trigger

Wave 1 stabilized the reasoning protocol and improved architectural discipline,
but the 2026-03-25 post-Wave-1 UBI benchmark showed the remaining gap clearly:

- Pipeline still loses the fair comparison against Perplexity on UBI
- Pipeline beats the single-shot baseline on the same evidence bundle
- Therefore the multi-analyst architecture is adding value, but the remaining
  weakness is now concentrated in retrieval quality, evidence anchoring, and
  dense-claim canonicalization

Observed in the UBI benchmark:

- important PDFs failed during collection because `llama_cloud` was missing
- claim extraction hallucinated invalid evidence/source IDs repeatedly
- dedup produced one invalid result and one invalid retry, then fell back to
  1:1 promotion on a dense 47-claim set
- the report cited canonical claims that had no evidence IDs until the
  immediate post-benchmark extraction fix was added
- after the PDF and anchoring fixes, a clean rerun collected 50 sources, 99
  evidence items, 2 gaps, and 26 authoritative sources
- the resumed export from that clean rerun produced a grounded report with 28
  cited claims and 0 grounding warnings
- fair comparison still scored 20 vs Perplexity's 24, so retrieval and
  grounding improved integrity but did not close the benchmark gap
- the same Wave 2 bundle still beat the single-shot baseline, so the
  multi-analyst architecture continues to add value even though UBI still loses
  to Perplexity

---

## Goal

Recover performance on enumeration-heavy, study-dense questions without
changing the cheap-model development baseline.

Specifically:

1. strengthen evidence anchoring so extracted claims use valid evidence IDs
2. improve PDF-heavy evidence retrieval so high-value studies are not dropped
3. prevent dense claim sets from collapsing dedup into repeated 1:1 fallback
4. keep report grounding strict enough that cited claims always resolve to
   evidence-bearing ledger entries

---

## Files Likely Affected

- `src/grounded_research/tools/fetch_page.py`
- `src/grounded_research/canonicalize.py`
- `prompts/claimify.yaml`
- `prompts/dedup.yaml`
- `tests/test_canonicalize.py`
- `tests/test_phase_boundaries.py`
- `docs/JUDGE_CRITIQUES.md`
- `docs/COMPETITIVE_ANALYSIS.md`

---

## Plan

### 1. Fix study/PDF retrieval on supported environments

Pre-make the environment decision:

- either install and support the current PDF parser dependency path
- or replace it with a supported parser/fallback that works in the standard dev
  environment

Do not leave study access dependent on an optional missing package.

Status:
- local-first PDF parsing implemented in `fetch_page.py`
- verified on a previously failing NBER UBI paper (`w27351.pdf`) using local `pypdf`
- clean UBI rerun collected 26 authoritative sources (up from 9 pre-fix and 20
  in the interrupted post-fix collection check)
- sub-question query generation now carries explicit parent-question topic
  anchors and mechanically re-anchors queries that drift away from the core
  intervention/topic
- the anchored-query rerun removed the prior off-topic subgroup-literature
  error, but the fair comparison worsened to 17 vs Perplexity's 25
- collection review showed the remaining issue more clearly: source selection
  still happens before source-quality scoring and currently round-robins raw
  search results, so weaker sources can crowd out stronger academic/government
  sources even when the right domains were already present in search results
- pre-fetch source-quality scoring is now wired into selection; a search-only
  validation on the UBI query set selected 50 URLs with `32 authoritative`,
  `7 reliable`, and `11 unknown` candidates, with the top of the set dominated
  by NBER, PMC, Stanford, Berkeley, IMF, and World Bank sources

### 2. Tighten Claimify evidence anchoring

Make Claimify harder to drift:

- present a smaller explicit candidate set of valid `E-...` IDs
- make the prompt say that claims without valid evidence must not be returned
- add post-parse accounting so dropped claims are counted and visible

The success condition is not just “fewer bad IDs.” It is “fewer valuable claims
lost because the model failed to anchor them correctly.”

Status:
- prompt now enumerates valid evidence IDs explicitly
- claim-extraction response schema now constrains `evidence_ids` to the run's
  actual candidate `E-...` IDs
- clean UBI rerun and resumed export finished with 40 claims and 0 claims
  lacking evidence IDs

### 3. Add dense-claim dedup strategy

The current retry guard is correct but insufficient on enumeration-heavy runs.
Pre-make the next implementation choice:

- keep the validator and retry
- add a staged dedup path for dense claim sets instead of sending the whole set
  through one grouping call

Examples:

- bucket by theme or entity first, then dedup within buckets
- or perform pairwise/non-merge screening before equivalence grouping

Do not accept repeated 1:1 fallback as a normal outcome on benchmark questions.

Current benchmark signal:

- the clean Wave 2 UBI rerun did not emit the prior invalid-group + retry
  warnings
- however, canonicalization still produced `40 raw -> 40 canonical`, so dense
  claim sets remain effectively under-canonicalized on this question even
  without an explicit 1:1 fallback event

Status:
- staged bucketed dedup is now implemented in `canonicalize.py`
- dense runs are partitioned conservatively by evidence overlap and informative
  token/entity overlap before per-bucket dedup
- unit and phase-boundary tests pass
- UBI rerun gate still pending

### 4. Add benchmark-level acceptance checks

Use UBI as the first gate question for this wave.

Required checks:

- no cited canonical claim has empty `evidence_ids`
- claim extraction drops fewer ungrounded claims than the 2026-03-25 UBI rerun
- dedup does not end in 1:1 fallback on the UBI benchmark
- fair comparison score against cached Perplexity report improves over the
  post-Wave-1 UBI run
- if the score does not improve, inspect whether the remaining loss is driven
  more by enumeration coverage or by weak canonical merging before changing
  retrieval again
- current diagnosis after the anchored-query rerun: retrieval still needs a
  mechanical ranking layer before fetch, not another prompt-only query tweak

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| PDF retrieval improves technically but still misses the key studies | UBI bundle still lacks NBER/IZA/World Bank/IMF evidence | inspect source coverage directly and adjust parser/fetch path before touching prompts |
| Claimify stops returning invalid IDs by becoming too conservative | extracted claim count collapses or specific pilot findings disappear | tighten evidence presentation, not just negative instructions |
| Dense-claim dedup reduces fallback but over-merges distinct pilots | canonical claim count drops sharply and dispute diversity collapses | strengthen non-merge criteria and inspect raw-to-canonical mapping before accepting |
| Grounding becomes stricter by silently dropping too much content | report quality drops while structural warnings improve | review dropped-claim accounting and restore only evidence-linked claims |

---

## Acceptance Criteria

- [ ] Standard environment can retrieve the key study PDFs needed for UBI-like questions
- [ ] Claimify no longer routinely invents invalid evidence/source IDs on the UBI benchmark
- [x] No cited claim in the final report lacks evidence IDs
- [ ] UBI dedup completes without ineffective `raw == canonical` non-merging on dense UBI runs
- [ ] Fair comparison vs cached Perplexity improves from the current post-Wave-1 UBI result
- [x] Pipeline still beats the single-shot baseline on the same bundle

---

## Notes

- This wave is intentionally narrower than a general “make everything better”
  pass. It is the benchmark-driven follow-up to the first stabilized reasoning
  wave.
- Do not switch production models for this wave. Fix the method on the cheap
  development stack first.
- 2026-03-25 benchmark result:
  - `output/ubi_wave2_full/` captured the clean raw-question rerun through
    adjudication before export failed on shared observability DB contention
  - `output/ubi_wave2_export_resume/` resumed export successfully from the
    saved trace using an isolated observability DB and explicit request
    timeouts
  - fair comparison vs cached Perplexity remained `20` vs `24`
  - fair comparison vs the same-bundle single-shot baseline favored the
    pipeline strongly
