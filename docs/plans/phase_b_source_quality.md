# Phase B: Source Quality & Evidence Intelligence

**Status:** Completed (2026-03-24)
**Depends on:** Phase A (decomposition — need sub-questions for sufficiency checks)
**Scorecard items:** #15, #18, #19

## Problem

All 50 sources default to `quality_tier="reliable"`. An EPA regulatory document
and a random blog post get equal weight in analyst reasoning and synthesis. With
96+ evidence items, the context is large and full of redundancy — a government
report and three blog posts restating it all compete for attention.

The fasting comparison loss to Perplexity (20 vs 25) was partly because Perplexity
differentiated source quality: "a meta-analysis of 12 RCTs" vs "one blogger's
experience." Our pipeline treats them the same.

## What To Build

### B.1: LLM Source Quality Scoring

After page fetch, before analyst phase. Single LLM call scores a batch of
sources. Not per-source (too many calls) — batch the URLs + titles + snippets
and get back quality tiers.

**Schema:**
```python
class SourceQualityAssessment(BaseModel):
    source_id: str
    quality_tier: Literal["authoritative", "reliable", "unknown", "unreliable"]
    reasoning: str  # one sentence explaining the tier
```

**Tiers:**
- `authoritative`: government agencies, peer-reviewed journals, major IGOs (WHO, IEA, EPA), established think tanks (Brookings, CSIS, Bruegel)
- `reliable`: major news outlets, professional organizations, well-known industry sources
- `unknown`: blogs, forums, small sites, unclear provenance
- `unreliable`: known misinformation sources, SEO farms, content mills

**Call shape:** One LLM call with all source URLs + titles + snippets → batch
of SourceQualityAssessment. Model: same as dispute_classification (gemini-2.5-flash).

**Where it goes:** `SourceRecord.quality_tier` is updated in the bundle after scoring.
Already flows to analyst prompt and synthesis prompt (both render quality_tier).

### B.2: Per-Sub-Question Evidence Sufficiency

After evidence collection, before analysts. Check whether each sub-question
has adequate source coverage.

**Logic (code, not LLM):**
- For each sub-question, count evidence items whose `search_query` originated
  from that sub-question's query generation
- Flag sub-questions with < 2 evidence items as gaps
- Add flagged gaps to `EvidenceBundle.gaps`

**Requires:** Tagging evidence items with which sub-question generated the search
query that found them. This means `collect.py` needs to track the sub-question
origin through the search → fetch → evidence chain.

### B.3: Conflict-Aware Compression

Before analyst phase, if evidence count exceeds a threshold (configurable,
default 80). Reduce redundant evidence while preserving:
- All evidence from `authoritative` sources
- Evidence that appears to conflict (different conclusions on same topic)
- At least one evidence item per sub-question

**Approach:** LLM-based. Send all evidence items, ask to identify redundant
clusters and select the most informative representative from each. Drop
the redundant ones. Keep all authoritative-source evidence regardless.

**Not for v1:** Semantic similarity detection, embedding-based clustering.
The LLM can do this in one call.

## Pre-Made Decisions

1. **Scoring model:** `gemini/gemini-2.5-flash` (same as dispute classification — needs judgment, single call)
2. **Config key:** `models.source_scoring` in config.yaml
3. **Batch vs per-source:** Batch scoring (one call for all 50 sources, not 50 calls)
4. **Compression threshold:** 80 evidence items (configurable in config.yaml as `evidence_policy.compression_threshold`)
5. **Compression model:** Same as scoring model
6. **Where scoring runs:** In `collect_evidence()` after fetch, before returning bundle. New function `score_source_quality()`.
7. **Where sufficiency runs:** In `engine.py` after collection, before analysts. Adds gaps to bundle.
8. **Where compression runs:** In `engine.py` after sufficiency check, before analysts. Modifies bundle in place.
9. **Evidence tagging:** `EvidenceItem` gets optional `sub_question_id: str | None` field. Set during query generation in `collect.py`.
10. **No new prompt files for scoring** — inline prompt in the scoring function (it's a simple classification, not a multi-turn reasoning task)

## Contracts

### B.1 Source Quality Scoring
```
in:  list[SourceRecord] with URLs + titles
out: list[SourceRecord] with quality_tier updated (was all "reliable", now per-source)
fail: LLM call fails → warn, keep all as "reliable" (graceful degradation)
```

### B.2 Evidence Sufficiency
```
in:  EvidenceBundle + QuestionDecomposition
out: EvidenceBundle with gaps added for under-covered sub-questions
fail: no sub-questions available → skip (backward compatible)
```

### B.3 Conflict-Aware Compression
```
in:  EvidenceBundle (possibly 96+ items)
out: EvidenceBundle (≤ threshold items, conflicts preserved, authoritative preserved)
fail: LLM call fails → warn, keep all evidence (no compression)
```

## Acceptance Criteria

**B.1 passes if:**
- EPA/WHO/IEA sources score "authoritative"
- Random blogs/forums score "unknown" or "unreliable"
- Quality tiers visible in analyst prompt context (already rendered — just need real values)
- Scoring adds < $0.01 to pipeline cost

**B.2 passes if:**
- Sub-question with 0 evidence items gets flagged as a gap
- Gap message includes the sub-question text
- Gaps visible in final report's "Evidence Gaps" section

**B.3 passes if:**
- Evidence count reduced to ≤ threshold
- No authoritative-source evidence dropped
- Conflicting evidence preserved (both sides of a dispute survive compression)
- Pipeline still produces valid output (no broken evidence ID references)

**Phase B gate (overall):**
- Re-run fasting question with all three features
- Fair comparison vs Perplexity: completeness score improves from 4 to ≥ 5
- No regression on decision usefulness (must stay ≥ 4)

## Failure Modes

| Failure | Diagnosis | Recovery |
|---------|-----------|----------|
| LLM scoring returns invalid tiers | Validation in code — unknown tiers → "unknown" | Graceful, logged warning |
| All sources scored "unknown" | LLM didn't understand the task | Check prompt, verify URLs/titles are in context |
| Compression drops critical evidence | Check if evidence IDs in claims still resolve | Raise compression threshold or disable |
| Sufficiency check too strict | Every sub-question flagged | Lower threshold from 2 to 1 |
| Context too large for batch scoring | Token limit exceeded | Split into batches of 25 |

## Implementation Sequence

1. Add `sub_question_id` field to `EvidenceItem` in models.py
2. Tag evidence items with sub-question origin in collect.py
3. Write `score_source_quality()` in new `src/grounded_research/source_quality.py`
4. Wire scoring into `collect_evidence()` (after fetch, before return)
5. Write evidence sufficiency check in engine.py (after collection)
6. Write conflict-aware compression in new `src/grounded_research/compress.py`
7. Wire compression into engine.py (after sufficiency, before analysts)
8. Add config keys: `models.source_scoring`, `evidence_policy.compression_threshold`
9. Run tests, verify on fasting question
10. Gate comparison vs Perplexity
